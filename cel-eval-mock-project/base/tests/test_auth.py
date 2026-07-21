"""T05 鉴权测试 —— main 分支全部通过。"""

import pytest
from src.auth import validate_token
from src.errors import AuthError


def test_validate_valid_token():
    payload = validate_token("valid-token")
    assert payload["user"] == "admin"


def test_validate_expired_token():
    """过期 token 应抛 AuthError。"""
    with pytest.raises(AuthError):
        validate_token("expired-token")


def test_validate_invalid_token():
    with pytest.raises(AuthError):
        validate_token("not-a-token")


def test_validate_token_returns_role():
    """返回的 payload 应包含 role 字段。"""
    payload = validate_token("valid-token")
    assert payload["role"] == "admin"
