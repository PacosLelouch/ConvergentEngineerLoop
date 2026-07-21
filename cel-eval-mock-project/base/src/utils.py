"""工具函数 —— T08 涉及。"""

import json


def load_config(path: str) -> dict:
    """加载 JSON 配置文件。"""
    with open(path, "r") as f:
        return json.load(f)
