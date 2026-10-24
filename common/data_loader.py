"""YAML 用例数据加载与占位符替换（数据驱动的地基）。

数据驱动原则：data/ 目录里的 YAML 描述"测什么"，testcases/ 里的通用执行器
描述"怎么测"——新增一条同接口用例只需在 YAML 里加几行，零 Python 代码。
"""

import os
import re

import yaml

from common.config_loader import PROJECT_ROOT

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# 匹配 {{变量名}} 占位符（链路提取变量用）
_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def load_cases(filename: str) -> list[dict]:
    """读 data/<filename>，返回 cases 列表。每个元素是一条用例的完整描述。"""
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
    cases = content.get("cases")
    if not cases:
        raise ValueError(f"{path} 中没有找到 cases 列表")
    return cases


def substitute(obj, context: dict):
    """递归替换 obj 里的 {{var}} 占位符。

    整值命中时保留原始类型（如 {{order_id}} 替换成 int 12 而不是字符串 "12"），
    字符串内嵌时转成字符串拼接（如 "订单{{order_no}}"）。
    """
    if isinstance(obj, dict):
        return {k: substitute(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute(v, context) for v in obj]
    if isinstance(obj, str):
        match = _PLACEHOLDER.fullmatch(obj.strip())
        if match and match.group(1) in context:
            return context[match.group(1)]
        return _PLACEHOLDER.sub(
            lambda m: str(context[m.group(1)]) if m.group(1) in context else m.group(0), obj)
    return obj
