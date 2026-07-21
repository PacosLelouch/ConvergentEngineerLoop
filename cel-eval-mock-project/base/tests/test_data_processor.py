"""T04 数据处理测试 —— main 分支全部通过。"""

from src.data_processor import transform_data
from src.report import generate_report


def test_transform_empty_list():
    """空列表应返回空列表。"""
    result = transform_data([])
    assert result == []


def test_transform_normal():
    result = transform_data([1, 2, 3])
    assert result == [2, 4, 6]


def test_transform_skip_none():
    """包含 None 的数据应跳过 None 值。"""
    result = transform_data([1, None, 2])
    assert result == [2, 4]


def test_generate_report():
    result = generate_report([1, 2])
    assert "item: 2" in result
    assert "item: 4" in result


def test_generate_report_empty():
    result = generate_report([])
    assert "empty" in result.lower()


def test_generate_report_with_none():
    """包含 None 的报告生成。"""
    result = generate_report([1, None, 2])
    assert "item: 2" in result
    assert "item: 4" in result
