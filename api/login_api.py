"""认证域接口封装：登录 / 注册 / 个人信息。

参数带默认值 None 的设计：数据驱动用例里"缺少某个参数"的反向用例，
靠"不传该参数"来构造，api 层负责把 None 字段从请求体里剔除。
"""

from api.base_api import BaseApi


class LoginApi(BaseApi):

    def login(self, username: str = None, password: str = None):
        """POST /api/auth/login
        成功: code 0, data={token, expires_in, user}
        失败: 1001 用户不存在 / 1002 密码错误 / 1004 参数缺失
        """
        body = {"username": username, "password": password}
        body = {k: v for k, v in body.items() if v is not None}
        return self.client.post("/api/auth/login", json_body=body)

    def register(self, username: str = None, password: str = None, nickname: str = None):
        """POST /api/auth/register 成功: code 0, data={user_id, username}；重名 1003。"""
        body = {"username": username, "password": password, "nickname": nickname}
        body = {k: v for k, v in body.items() if v is not None}
        return self.client.post("/api/auth/register", json_body=body)

    def me(self):
        """GET /api/auth/me —— token 由 RestClient 自动附带；未登录 401/4010。"""
        return self.client.get("/api/auth/me")

    def me_with_token(self, token: str):
        """用显式传入的 token 请求个人信息——专门测伪造/无效 token 场景。"""
        return self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
