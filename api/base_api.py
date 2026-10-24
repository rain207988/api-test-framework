"""接口业务封装基类。

分层规则（S5 确立）：
- URL、参数结构这些"接口知识"只出现在 api/ 层；
- 用例层只允许调用这里的业务方法，禁止出现 url 字符串和 requests 调用；
- 接口路径变了，只需要改 api/ 层对应文件，所有用例自动跟随。
"""


class BaseApi:
    def __init__(self, client):
        """client: common.rest_client.RestClient 实例（token 已由上层注入）。"""
        self.client = client
