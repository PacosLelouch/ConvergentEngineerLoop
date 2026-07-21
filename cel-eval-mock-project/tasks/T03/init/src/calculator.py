"""计算器模块 —— T03 涉及。"""

from .errors import DivisionByZeroError


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    """除法 —— T03 缺陷：函数体为 pass，待实现。"""
    pass
