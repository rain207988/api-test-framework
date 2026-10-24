"""登录域测试：数据驱动用例 + fixture 机制展示（手写用例）。

这个文件同时演示两种用例写法：
- TestLoginApi：数据驱动——用例内容全在 data/login_data.yaml，Python 只负责"翻译执行"；
- TestTokenFixture：手写用例——演示 token 如何通过 fixture 注入（S4 的核心机制）。
"""

import allure
import pytest

from api.login_api import LoginApi
from common.assertions import assert_response
from common.data_loader import load_cases
from testcases.api_registry import run_single_case


@allure.feature("登录模块")
class TestLoginApi:
    """数据驱动：login_data.yaml 里的每条 case 自动变成一个独立用例。"""

    @pytest.mark.parametrize("case", load_cases("login_data.yaml"), ids=lambda c: c["name"])
    def test_login_api(self, case, rest_client, fresh_client):
        # no_auth 的用例换干净客户端，其余用主客户端（token 已注入）
        client = fresh_client if case.get("no_auth") else rest_client
        run_single_case(case, client, context=case["name"])


@allure.feature("登录模块")
@allure.story("token 注入机制")
class TestTokenFixture:
    """手写用例：验证 fixture 注入的 token 真实生效（面试演示用）。"""

    def test_rest_client_token_injected(self, rest_client):
        """主客户端自带 token：直接调需鉴权接口应成功，且响应里是主账号。"""
        resp = LoginApi(rest_client).me()
        body = resp.json()
        assert resp.status_code == 200
        assert body["code"] == 0
        assert body["data"]["username"] == "lemon"

    def test_fresh_client_without_token(self, fresh_client):
        """干净客户端无 token：需鉴权接口必须返回 401 + 业务码 4010。"""
        resp = LoginApi(fresh_client).me()
        assert resp.status_code == 401
        assert resp.json()["code"] == 4010

    def test_wrong_password_does_not_break_session_token(self, rest_client):
        """用错误密码再登录一次，不影响会话里已有的有效 token（登录与鉴权解耦）。"""
        bad = LoginApi(rest_client).login("lemon", "wrong-pass")
        assert_response(bad, {"code": 1002})
        good = LoginApi(rest_client).me()
        assert_response(good, {"status_code": 200, "code": 0,
                               "fields": {"$.data.username": "lemon"}})
