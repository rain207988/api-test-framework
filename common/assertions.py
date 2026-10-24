"""三层断言 + JSONPath 提取（框架的"裁判"，面试必讲模块）。

三层断言为什么缺一不可（以 demo-mall 为例）：
①HTTP 状态码：4010 未登录时服务端返回 HTTP 401——只看业务码会漏掉鉴权层问题；
②业务 code：业务失败时服务端返回 HTTP 200 + code=1002——只看 HTTP 状态码
  会把"密码错误"也当成通过，这是国内系统最常见的响应约定；
③关键字段：code=0 不代表数据对，还得用 JSONPath 抽查具体返回值
 （如 $.data.user.username 必须是 lemon）。

断言失败时打印"请求+响应全文"，做到"看报错即定位"，不用重跑抓包。
"""

import json

import requests
from jsonpath import jsonpath


def extract_jsonpath(data, expr: str):
    """按 JSONPath 取值；命中返回第一个值，未命中返回 None。"""
    matches = jsonpath(data, expr)
    return matches[0] if matches else None


def assert_response(resp: requests.Response, expect: dict | None = None, context: str = ""):
    """对一次 HTTP 响应做三层断言。

    expect 结构（YAML 里同构）：
        status_code: 200        # 第①层，可选
        code: 0                 # 第②层，可选
        fields:                 # 第③层，可选，JSONPath -> 期望值
            "$.data.user.username": "lemon"
    """
    expect = expect or {}

    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = None

    # ---- 第①层：HTTP 状态码 ----
    if "status_code" in expect:
        _check(resp, f"HTTP状态码", expect["status_code"], resp.status_code, context, body)

    # ---- 第②层：业务错误码 ----
    if "code" in expect:
        if body is None:
            _raise_fail(resp, "业务code", expect["code"], "响应体不是合法JSON", context)
        _check(resp, "业务code", expect["code"], body.get("code"), context, body)

    # ---- 第③层：关键字段（JSONPath） ----
    for expr, expected in (expect.get("fields") or {}).items():
        if body is None:
            _raise_fail(resp, f"字段 {expr}", expected, "响应体不是合法JSON", context)
        actual = extract_jsonpath(body, expr)
        if actual is None:
            _raise_fail(resp, f"字段 {expr}", expected, "JSONPath 未命中（字段不存在）", context)
        _check(resp, f"字段 {expr}", expected, actual, context, body)


def _check(resp, desc, expected, actual, context, body):
    if actual != expected:
        _raise_fail(resp, desc, expected, actual, context)


def _raise_fail(resp, desc, expected, actual, context):
    req = resp.request
    req_body = req.body
    if isinstance(req_body, bytes):
        req_body = req_body.decode("utf-8", errors="replace")
    detail = (
        f"\n{'=' * 20} 断言失败 {'=' * 20}\n"
        f"用例上下文: {context or '-'}\n"
        f"检查项    : {desc}\n"
        f"期望值    : {expected!r}\n"
        f"实际值    : {actual!r}\n"
        f"{'-' * 20} 请求 {'-' * 20}\n"
        f"{req.method} {req.url}\n"
        f"请求体    : {req_body}\n"
        f"{'-' * 20} 响应 {'-' * 20}\n"
        f"HTTP {resp.status_code} ({resp.elapsed.total_seconds() * 1000:.0f}ms)\n"
        f"响应体    : {resp.text[:2000]}\n"
        f"{'=' * 51}"
    )
    raise AssertionError(detail)
