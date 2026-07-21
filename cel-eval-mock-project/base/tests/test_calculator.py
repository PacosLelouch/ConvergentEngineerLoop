"""T03 计算器测试 —— main 分支全部通过。"""

import pytest
from src.calculator import add, subtract, multiply, divide
from src.errors import DivisionByZeroError


def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0


def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5


def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(0, 5) == 0


def test_divide_normal():
    assert divide(10, 2) == 5
    assert divide(7, 2) == 3.5


def test_divide_by_zero():
    with pytest.raises(DivisionByZeroError):
        divide(10, 0)
