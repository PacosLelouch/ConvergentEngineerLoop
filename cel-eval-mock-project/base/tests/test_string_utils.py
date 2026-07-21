"""T06 字符串工具测试 —— main 分支全部通过。"""

from src.string_utils import truncate


def test_truncate_short_text():
    assert truncate("hello", 10) == "hello"


def test_truncate_long_text():
    assert truncate("hello world", 5) == "hello..."


def test_truncate_exact_length():
    assert truncate("hello", 5) == "hello"
