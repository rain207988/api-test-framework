"""RestClient：全框架唯一的 HTTP 出口。

为什么所有请求都走这一个类（而不是用例里直接 import requests）：
1. 统一 base_url / 超时 / Header（token 注入点）——环境切换改配置即可；
2. 统一日志：每条请求响应在日志里都有迹可查，失败排查不用猜；
3. 统一异常翻译：连接拒绝/超时等网络错误转成带上下文的 ApiError，
   用例里看到的不再是裸 traceback；
4. 统一 401 策略：token 失效时调用注入的 relogin_hook 重登并重放一次（S7 机制）。

依赖方向：common 层不 import api 层（避免循环依赖）；401 后"怎么重新登录"
由上层（conftest）以回调形式注入，这叫依赖倒置。
"""

import json as jsonlib

import requests

from common.config_loader import get_config
from common.logger import get_logger

log = get_logger("rest_client")


class ApiError(Exception):
    """请求根本没有到达服务器（连接失败/超时）时抛出。

    与"业务失败"（HTTP 200 + code!=0）严格区分：
    前者是框架/环境问题，后者是被测系统的行为，测试要断言的恰恰是后者。
    """


class RestClient:
    def __init__(self, base_url: str = None, timeout: int = None, relogin_hook=None):
        cfg = get_config()
        self.base_url = (base_url or cfg.base_url).rstrip("/")
        self.timeout = timeout or cfg.timeout
        self.relogin_hook = relogin_hook     # 形如 lambda: "新token" 的回调，未配置则 401 原样返回
        self.session = requests.Session()    # Session 复用 TCP 连接，批量用例明显提速
        self.token: str | None = None

    # ---------- token 管理 ----------

    def set_token(self, token: str | None):
        """注入 token。之后所有请求自动带 Authorization: Bearer <token>。"""
        self.token = token

    # ---------- 核心请求方法 ----------

    def request(self, method: str, path: str, params: dict = None,
                json_body=None, headers: dict = None, _auth_retry: bool = True) -> requests.Response:
        url = self.base_url + path

        req_headers = {"Accept": "application/json"}
        if self.token:
            req_headers["Authorization"] = f"Bearer {self.token}"
        if headers:
            req_headers.update(headers)

        log.info("-> %s %s params=%s body=%s", method, path, params,
                 jsonlib.dumps(json_body, ensure_ascii=False) if json_body else None)
        log.debug("请求头: %s", req_headers)

        try:
            resp = self.session.request(method, url, params=params, json=json_body,
                                        headers=req_headers, timeout=self.timeout)
        except requests.RequestException as exc:
            log.error("请求失败: %s %s - %s", method, url, exc)
            raise ApiError(f"请求 {method} {url} 失败：{exc}") from exc

        cost_ms = resp.elapsed.total_seconds() * 1000
        log.info("<- HTTP %s (%.0fms) %s", resp.status_code, cost_ms, path)
        log.debug("响应体: %s", resp.text[:2000])

        # ---- token 失效自动重登并重放一次 ----
        # 只重放一次（_auth_retry=False），防止"账号本身有问题"时无限重登
        if resp.status_code == 401 and _auth_retry and self.relogin_hook:
            log.warning("收到 401，尝试自动重新登录并重放: %s", path)
            new_token = self.relogin_hook()
            if new_token:
                self.set_token(new_token)
                return self.request(method, path, params=params, json_body=json_body,
                                    headers=headers, _auth_retry=False)
        return resp

    # ---------- 语义化快捷方法 ----------

    def get(self, path, params=None, headers=None):
        return self.request("GET", path, params=params, headers=headers)

    def post(self, path, json_body=None, headers=None):
        return self.request("POST", path, json_body=json_body, headers=headers)

    def put(self, path, json_body=None, headers=None):
        return self.request("PUT", path, json_body=json_body, headers=headers)

    def delete(self, path, headers=None):
        return self.request("DELETE", path, headers=headers)
