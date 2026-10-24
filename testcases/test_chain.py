"""业务链路测试：YAML 步骤编排（S7 的核心成果）。

一条链路 = 多个步骤按序执行 + 变量在步骤间传递：
- 登录步骤提取 token → 自动注入后续请求头；
- 下单步骤提取 order_id → 后续查单/支付/取消用 {{order_id}} 占位符引用。

链路数据在 data/chain_data.yaml；新增一条业务链路同样零 Python 代码。
"""

import allure
import pytest

from common.data_loader import load_cases
from testcases.api_registry import run_chain


@allure.feature("业务链路")
class TestBusinessChain:
    @pytest.mark.parametrize("case", load_cases("chain_data.yaml"), ids=lambda c: c["name"])
    def test_chain(self, case, chain_client):
        run_chain(chain_client, case)
