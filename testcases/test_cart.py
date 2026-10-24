"""购物车域测试：纯数据驱动（反向用例为主，正向链路见 test_chain.py）。

执行顺序说明：pytest 按文件名字母序收集，test_chain.py 在本文件之前执行，
链路结束时主账号购物车为空，因此"购物车结构正常"用例可以断言 count=0。
"""

import allure
import pytest

from common.data_loader import load_cases
from testcases.api_registry import run_single_case


@allure.feature("购物车模块")
class TestCartApi:
    @pytest.mark.parametrize("case", load_cases("cart_data.yaml"), ids=lambda c: c["name"])
    def test_cart_api(self, case, rest_client, fresh_client):
        client = fresh_client if case.get("no_auth") else rest_client
        run_single_case(case, client, context=case["name"])
