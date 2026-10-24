"""商品域测试：纯数据驱动。

这个文件是"新增用例零 Python 代码"的样板——想加用例？
直接在 data/goods_data.yaml 的 cases 里加一段即可，本文件永远不用改。
"""

import allure
import pytest

from common.data_loader import load_cases
from testcases.api_registry import run_single_case


@allure.feature("商品模块")
class TestGoodsApi:
    """查询类接口（无需登录），断言依赖种子数据的确定性。"""

    @pytest.mark.parametrize("case", load_cases("goods_data.yaml"), ids=lambda c: c["name"])
    def test_goods_api(self, case, rest_client, fresh_client):
        client = fresh_client if case.get("no_auth") else rest_client
        run_single_case(case, client, context=case["name"])
