"""T05 鉴权测试 —— init 分支有 3 个失败。"""

import pytest
from src.auth import validate_token
from src.errors import AuthError


def test_validate_valid_token():
    payload = validate_token("valid-token")
    assert payload["user"] == "admin"
    assert payload["role"] == "Admin"


def test_validate_expired_token():
    """过期 token 应抛 AuthError。init: 代码返回 200 而非抛异常，此测试失败。"""
    with pytest.raises(AuthError):
        validate_token("expired-token")


def test_validate_invalid_token():
    with pytest.raises(AuthError):
        validate_token("not-a-token")


def test_validate_token_returns_role():
    payload = validate_token("valid-token")
    assert payload["role"] == "admin"  # 大小写不一致：代码 "Admin" vs 测试 "admin"
