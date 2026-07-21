"""用户服务 —— T01 涉及。"""

from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


_USERS = {
    1: User(id=1, name="Alice"),
    2: User(id=2, name="Bob"),
}


def get_user_by_id(user_id: int) -> User | None:
    """按 ID 查询用户。

    T01 缺陷：缺少 None 检查，user_id 不存在时访问 user.name 会抛 NoneTypeError。
    """
    user = _USERS.get(user_id)
    return user
