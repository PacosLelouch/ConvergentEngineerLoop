"""工具函数 —— T08 缺陷：缺少 docstring。"""

import json


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)
