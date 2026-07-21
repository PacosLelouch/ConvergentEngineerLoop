"""测试配置。"""
import pytest


@pytest.fixture
def sample_users():
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]
