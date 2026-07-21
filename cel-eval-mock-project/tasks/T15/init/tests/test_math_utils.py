"""T15 数学工具测试 —— init 分支 5 个失败。"""

import pytest
from src.math_utils import calculate_statistics


def test_normal_values():
    result = calculate_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["count"] == 5
    assert result["mean"] == 3.0


def test_even_count():
    result = calculate_statistics([1.0, 2.0, 3.0, 4.0])
    assert result["count"] == 4
    assert result["median"] == 2.5


def test_all_none_raises():
    """init：全部 None 因首个为 None 抛异常。"""
    with pytest.raises(ValueError):
        calculate_statistics([None, None, None])


def test_mixed_none():
    """init：首个为 None 抛异常（而非跳过）。"""
    with pytest.raises(ValueError):
        calculate_statistics([None, 1.0, 3.0])


def test_mixed_none_middle():
    """None 在中间应跳过。"""
    result = calculate_statistics([1.0, None, 3.0])
    assert result["count"] == 2


def test_empty_list():
    result = calculate_statistics([])
    assert result["count"] == 0


def test_negative_values():
    result = calculate_statistics([-5.0, 0.0, 5.0])
    assert result["mean"] == 0.0
