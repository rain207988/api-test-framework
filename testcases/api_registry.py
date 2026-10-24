"""api 层注册表 + 用例执行器：YAML 数据驱动的"引擎"。

为什么需要注册表：
- YAML 里只写 api 的名字（如 login），不写 URL——保证"URL 只出现在 api 层"的分层铁律；
- 注册表把名字映射到 api 层方法。要支持新接口，只需：api 层加一个方法 + 这里加一行映射；
- 之后新增同接口的用例 = 只在 data/ 加 YAML，零 Python 代码（S6 的验收目标）。

run_step / run_chain 是"小执行器"：读步骤 → 替换占位符 → 调 api → 断言 → 提取变量。
它故意写得很直白（不到 60 行），方便你面试时讲清"数据驱动到底怎么跑起来的"。
"""

import allure

from api.cart_api import CartApi
from api.goods_api import GoodsApi
from api.login_api import LoginApi
from api.order_api import OrderApi
from api.test_support_api import TestSupportApi
from common.assertions import assert_response, extract_jsonpath
from common.data_loader import substitute
from common.logger import get_logger

log = get_logger("case_runner")


# ---------------- 注册表：api 名字 -> 执行函数 ----------------

def _login(c, p):
    return LoginApi(c).login(**p)


def _register(c, p):
    return LoginApi(c).register(**p)


REGISTRY = {
    "login":         _login,
    "register":      _register,
    "me":            lambda c, p: LoginApi(c).me(),
    "me_with_token": lambda c, p: LoginApi(c).me_with_token(**p),
    "goods_list":    lambda c, p: GoodsApi(c).list_goods(**p),
    "goods_detail":  lambda c, p: GoodsApi(c).goods_detail(**p),
    "cart_get":      lambda c, p: CartApi(c).get_cart(),
    "cart_add":      lambda c, p: CartApi(c).add_cart(**p),
    "cart_update":   lambda c, p: CartApi(c).update_cart_item(**p),
    "cart_delete":   lambda c, p: CartApi(c).delete_cart_item(**p),
    "order_create":  lambda c, p: OrderApi(c).create_order(**p),
    "order_list":    lambda c, p: OrderApi(c).list_orders(**p),
    "order_detail":  lambda c, p: OrderApi(c).get_order(**p),
    "order_pay":     lambda c, p: OrderApi(c).pay_order(**p),
    "order_cancel":  lambda c, p: OrderApi(c).cancel_order(**p),
    "test_revoke":   lambda c, p: TestSupportApi(c).revoke_token(**p),
}


# ---------------- 执行器 ----------------

def attach_response(resp, name: str = "响应报文"):
    """把响应挂进 Allure 报告，失败时不用重跑就能看到现场。"""
    allure.attach(resp.text, name=name, attachment_type=allure.attachment_type.JSON)


def run_single_case(case: dict, client, context: str = ""):
    """执行一条单步 YAML 用例：查注册表 → 调 api → 三层断言。"""
    allure.dynamic.title(case["name"])
    func = REGISTRY[case["api"]]
    resp = func(client, substitute(case.get("params") or {}, {}))
    attach_response(resp)
    assert_response(resp, case.get("expect"), context=context or case["name"])
    return resp


def run_step(client, step: dict, context: dict):
    """执行链路中的一个步骤：断言 + 提取变量。"""
    with allure.step(step.get("name") or step["api"]):
        # params 和 expect 都要过占位符替换：expect 里也允许引用链路变量
        # （如断言"查单详情的 order_no 必须等于下单时提取到的 order_no"）
        params = substitute(step.get("params") or {}, context)
        expect = substitute(step.get("expect") or {}, context)
        resp = REGISTRY[step["api"]](client, params)
        attach_response(resp, name=f"步骤[{step.get('name', step['api'])}]响应")
        assert_response(resp, expect, context=step.get("name") or step["api"])

        for var, expr in (step.get("extract") or {}).items():
            value = extract_jsonpath(resp.json(), expr)
            if value is None:
                raise AssertionError(f"步骤[{step.get('name')}] 提取变量 {var} 失败：{expr} 未命中")
            context[var] = value
            log.debug("提取变量 %s = %r", var, value)
            # 链路约定：提取出的 token 立即注入客户端，后续步骤自动携带
            if var == "token":
                client.set_token(value)
    return resp


def run_chain(client, case: dict):
    """执行一条链路用例：多个步骤共享一个上下文，顺序执行。"""
    allure.dynamic.title(case["name"])
    context: dict = {}
    for step in case["steps"]:
        run_step(client, step, context)
    return context
