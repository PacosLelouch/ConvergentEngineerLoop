"""计算器模块 —— T03 涉及。"""

from .errors import DivisionByZeroError


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    """除法，b=0 时抛出 DivisionByZeroError。

    main 分支已正确实现。
    T03 测试分支此处为 pass（函数体待实现）。
    """
    if b == 0:
        raise DivisionByZeroError("除数不能为零")
    return a / b
