"""用户服务 —— T01 涉及。"""

from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


# 模拟数据库
_USERS = {
    1: User(id=1, name="Alice"),
    2: User(id=2, name="Bob"),
}


def get_user_by_id(user_id: int) -> User | None:
    """按 ID 查询用户，不存在时返回 None。

    注意：main 分支已正确处理 None。
    T01 测试分支会在此引入缺陷（缺少 None 检查）。
    """
    user = _USERS.get(user_id)
    if user is None:
        return None
    return user
