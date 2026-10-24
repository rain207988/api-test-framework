"""订单域测试：纯数据驱动（状态机流转的正向用例在 test_chain.py）。"""

import allure
import pytest

from common.data_loader import load_cases
from testcases.api_registry import run_single_case


@allure.feature("订单模块")
class TestOrderApi:
    @pytest.mark.parametrize("case", load_cases("order_data.yaml"), ids=lambda c: c["name"])
    def test_order_api(self, case, rest_client, fresh_client):
        client = fresh_client if case.get("no_auth") else rest_client
        run_single_case(case, client, context=case["name"])
