"""T08 API 测试 —— main 分支全部通过。"""

import pytest
from src.api import list_users, get_user, query_table, QueryRequest


def test_list_users():
    result = list_users()
    assert result["total"] == 2
    assert len(result["users"]) == 2


def test_get_user_valid():
    result = get_user(1)
    assert result["name"] == "User1"


def test_get_user_invalid():
    with pytest.raises(ValueError):
        get_user(0)


def test_query_valid_table():
    req = QueryRequest(table="users")
    result = query_table(req)
    assert result["table"] == "users"


def test_query_invalid_table():
    req = QueryRequest(table="secrets")
    with pytest.raises(ValueError):
        query_table(req)
