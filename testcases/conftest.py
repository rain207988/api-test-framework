"""全局 fixture：客户端、token、数据重置、Allure 环境。整个框架的"装配车间"。

fixture 依赖关系（读代码前先看这张图）：

    _reset_mall_data (session, autouse)   ← 跑任何用例前先重置被测系统数据
         │
    token_manager (session)               ← TokenManager（登录函数在此注入）
         │
    rest_client (session)                 ← 主客户端：已注入 token + 401 自动重登钩子
    fresh_client (session)                ← 干净客户端：无 token 无钩子（测未登录场景）
    chain_client (session)                ← 链路专用客户端：有钩子但初始无 token（与主客户端隔离）
"""

import os

import allure
import pytest

from api.login_api import LoginApi
from api.test_support_api import TestSupportApi
from common.config_loader import get_config
from common.logger import get_logger
from common.rest_client import RestClient
from common.token_manager import TokenManager

log = get_logger("conftest")


def _make_login_func():
    """构造 login_func(user_key) -> {"token":..,"user":..}，交给 TokenManager 缓存。

    用"裸客户端"（无 token、无钩子）登录，避免登录请求自己带上旧 token。
    """
    cfg = get_config()
    bare_client = RestClient(cfg.base_url, cfg.timeout)

    def login_func(user_key: str) -> dict:
        user = cfg.users[user_key]
        log.info("自动登录账号 [%s]: %s", user_key, user["username"])
        resp = LoginApi(bare_client).login(user["username"], user["password"])
        body = resp.json()
        if resp.status_code != 200 or body.get("code") != 0:
            raise RuntimeError(
                f"自动登录失败（账号 {user['username']}）：HTTP {resp.status_code}, 响应 {resp.text[:300]}。"
                f"请确认被测系统已启动、账号与 config.yaml 一致")
        return body["data"]

    return login_func


@pytest.fixture(scope="session", autouse=True)
def _reset_mall_data():
    """套件开始前把被测系统数据一键重置为种子状态——自动化可重复的基石。

    autouse=True：所有用例（不管在哪个文件）都隐式依赖它，保证不漏。
    """
    cfg = get_config()
    log.info("重置被测系统数据: POST %s/api/test/reset", cfg.base_url)
    resp = TestSupportApi(RestClient(cfg.base_url, cfg.timeout)).reset_data()
    if resp.status_code != 200 or resp.json().get("code") != 0:
        raise RuntimeError(f"数据重置失败：{resp.status_code} {resp.text[:300]}。"
                           f"请先启动 demo-mall（python run.py）")
    log.info("被测系统就绪: %s", cfg.base_url)


@pytest.fixture(scope="session")
def token_manager() -> TokenManager:
    return TokenManager(login_func=_make_login_func())


@pytest.fixture(scope="session")
def rest_client(token_manager) -> RestClient:
    """主客户端：session 级登录一次，token 全程复用；401 时自动重登重放。"""
    cfg = get_config()

    def relogin_hook():
        token_manager.invalidate("main")
        return token_manager.get_token("main")

    client = RestClient(cfg.base_url, cfg.timeout, relogin_hook=relogin_hook)
    client.set_token(token_manager.get_token("main"))
    return client


@pytest.fixture(scope="session")
def fresh_client() -> RestClient:
    """干净客户端：不带 token、无重登钩子——专门测"未登录"反向场景。"""
    cfg = get_config()
    return RestClient(cfg.base_url, cfg.timeout)


@pytest.fixture(scope="session")
def chain_client(token_manager) -> RestClient:
    """链路用例专用客户端：初始无 token（由链路第一步登录并注入）。

    与 rest_client 隔离的原因：链路会切换登录账号、吊销 token，
    不能污染其他单步用例正在使用的会话状态。
    """
    cfg = get_config()

    def relogin_hook():
        token_manager.invalidate("main")
        return token_manager.get_token("main")

    return RestClient(cfg.base_url, cfg.timeout, relogin_hook=relogin_hook)


def pytest_sessionfinish(session, exitstatus):
    """会话结束时把环境信息写进 Allure 结果目录（报告页首的 Environment 面板）。"""
    import sys

    alluredir = session.config.getoption("--alluredir", default=None)
    if not alluredir or not os.path.isdir(alluredir):
        return
    cfg = get_config()
    with open(os.path.join(alluredir, "environment.properties"), "w", encoding="utf-8") as f:
        f.write(f"base_url={cfg.base_url}\n")
        f.write(f"env={cfg.env}\n")
        f.write(f"python={sys.version.split()[0]}\n")
