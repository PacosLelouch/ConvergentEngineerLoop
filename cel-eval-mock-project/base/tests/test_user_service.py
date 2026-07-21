"""T01 用户服务测试 —— main 分支全部通过。"""

import pytest
from src.user_service import get_user_by_id, User


def test_get_existing_user():
    user = get_user_by_id(1)
    assert user is not None
    assert user.name == "Alice"


def test_get_another_user():
    user = get_user_by_id(2)
    assert user is not None
    assert user.name == "Bob"


def test_get_user_not_found():
    """不存在的用户应返回 None。"""
    user = get_user_by_id(999)
    assert user is None


def test_user_dataclass():
    u = User(id=3, name="Charlie")
    assert u.id == 3
    assert u.name == "Charlie"
