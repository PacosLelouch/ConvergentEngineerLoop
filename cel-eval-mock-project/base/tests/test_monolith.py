"""T11 单体模块测试 —— main 分支全部通过。"""

from src.monolith import (
    authenticate, check_permission,
    db_fetch, db_insert, cache_get, cache_set,
    get_user_with_role, get_all_products,
)


def test_authenticate_valid():
    assert authenticate("admin-token") == "admin"


def test_authenticate_invalid():
    import pytest
    with pytest.raises(ValueError):
        authenticate("bad-token")


def test_check_permission_admin():
    assert check_permission("admin", "write") is True


def test_check_permission_user_read():
    assert check_permission("user", "read") is True


def test_check_permission_user_write():
    assert check_permission("user", "write") is False


def test_db_fetch():
    users = db_fetch("users")
    assert len(users) == 2


def test_db_insert():
    db_insert("users", {"id": 3, "name": "Charlie"})
    users = db_fetch("users")
    assert len(users) == 3


def test_cache_set_get():
    cache_set("key1", "value1", ttl=10)
    assert cache_get("key1") == "value1"


def test_get_user_with_role():
    user = get_user_with_role("admin-token", 1)
    assert user is not None
    assert user["name"] == "Alice"


def test_get_all_products():
    products = get_all_products("admin-token")
    assert len(products) == 1
