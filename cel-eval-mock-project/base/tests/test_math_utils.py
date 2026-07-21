"""T15 数学工具测试 —— main 分支全部通过。

注：main 分支的 calculate_statistics 对 None 处理有意不一致。
"""

import pytest
from src.math_utils import calculate_statistics


def test_normal_values():
    result = calculate_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["count"] == 5
    assert result["mean"] == 3.0
    assert result["median"] == 3.0


def test_even_count():
    result = calculate_statistics([1.0, 2.0, 3.0, 4.0])
    assert result["count"] == 4
    assert result["median"] == 2.5


def test_all_none_raises():
    """全部 None 应抛 ValueError（main 分支行为）。"""
    with pytest.raises(ValueError):
        calculate_statistics([None, None, None])


def test_mixed_none():
    """含 None 和有效值的列表。"""
    result = calculate_statistics([1.0, None, 3.0])
    assert result["count"] == 2
    assert result["mean"] == 2.0
    assert result["median"] == 2.0


def test_single_value():
    result = calculate_statistics([42.0])
    assert result["count"] == 1
    assert result["mean"] == 42.0
    assert result["median"] == 42.0


def test_empty_list():
    result = calculate_statistics([])
    assert result["count"] == 0
    assert result["mean"] == 0.0
    assert result["median"] == 0.0


def test_negative_values():
    result = calculate_statistics([-5.0, 0.0, 5.0])
    assert result["count"] == 3
    assert result["mean"] == 0.0
    assert result["median"] == 0.0
