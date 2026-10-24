"""TokenManager：登录一次、全程复用、失效可刷新。

为什么需要它：
- 57 条用例如果每条都先登录，被测系统要多扛 57 次登录请求，套件也慢一截；
- token 过期/被吊销时（RestClient 的 401 hook）需要一个能"重新拿新 token"的入口；
- common 层不允许 import api 层（分层规则），所以登录动作以 login_func 回调注入——
  本类只管"缓存与刷新"策略，不关心登录接口长什么样。
"""


class TokenManager:
    def __init__(self, login_func):
        """login_func(user_key) -> {"token": ..., "user": {...}}，由 conftest 注入。"""
        self._login_func = login_func
        self._cache: dict[str, str] = {}

    def get_token(self, user_key: str = "main") -> str:
        """取 token：缓存命中直接返回，未命中登录一次并缓存。"""
        if user_key not in self._cache:
            info = self._login_func(user_key)
            self._cache[user_key] = info["token"]
        return self._cache[user_key]

    def invalidate(self, user_key: str = "main"):
        """作废缓存。401 重登 hook 的标准动作：先 invalidate 再 get_token。"""
        self._cache.pop(user_key, None)
