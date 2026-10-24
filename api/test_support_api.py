"""测试辅助域接口封装：数据重置 / token 吊销。

被测系统专门给自动化开的"测试后门"（X-Test-Key 鉴权）。
企业里对应"测试环境管理平台"的能力——自动化可重复的前提。
"""

from api.base_api import BaseApi
from common.config_loader import get_config


class TestSupportApi(BaseApi):

    def _test_headers(self):
        return {"X-Test-Key": get_config().test_key}

    def reset_data(self):
        """POST /api/test/reset —— 数据库还原为种子状态（跑套件前必须做）。"""
        return self.client.post("/api/test/reset", headers=self._test_headers())

    def revoke_token(self, token: str):
        """POST /api/test/revoke-token —— 吊销 token，制造真实 401，练自动重登。"""
        return self.client.post("/api/test/revoke-token",
                                json_body={"token": token}, headers=self._test_headers())
