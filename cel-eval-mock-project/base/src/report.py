"""报告生成模块 —— T04 涉及。"""

from .data_processor import transform_data


def generate_report(raw_data: list) -> str:
    """生成报告，依赖 transform_data 返回 list。"""
    processed = transform_data(raw_data)
    lines = [f"item: {x}" for x in processed]
    return "\n".join(lines) if lines else "(empty report)"
