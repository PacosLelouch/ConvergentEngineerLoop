"""单体模块 —— T11 涉及。

main 分支：所有功能正确，10 个集成测试通过。
T11 任务：要求拆分为 auth/db/cache 三个子模块。
"""

# === 认证部分 ===
_AUTH_TOKENS = {"admin-token": "admin", "user-token": "user"}


def authenticate(token: str) -> str:
    """验证 token，返回角色名。"""
    role = _AUTH_TOKENS.get(token)
    if role is None:
        raise ValueError("无效 token")
    return role


def check_permission(role: str, resource: str) -> bool:
    """检查角色是否有资源访问权限。"""
    if role == "admin":
        return True
    return resource in ("read",)


# === 数据库部分 ===
_DB: dict[str, list[dict]] = {
    "users":    [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    "products": [{"id": 1, "name": "Widget", "price": 9.99}],
}


def db_fetch(table: str) -> list[dict]:
    """从数据库获取数据。"""
    return _DB.get(table, [])


def db_insert(table: str, record: dict) -> bool:
    """向数据库插入记录。"""
    if table not in _DB:
        _DB[table] = []
    _DB[table].append(record)
    return True


# === 缓存部分 ===
_CACHE: dict[str, tuple] = {}


def cache_get(key: str) -> object | None:
    """从缓存读取。"""
    import time
    entry = _CACHE.get(key)
    if entry is None:
        return None
    value, expiry = entry
    if time.time() > expiry:
        del _CACHE[key]
        return None
    return value


def cache_set(key: str, value: object, ttl: int = 300) -> None:
    """写入缓存。"""
    import time
    _CACHE[key] = (value, time.time() + ttl)


# === 对外接口 ===
def get_user_with_role(token: str, user_id: int) -> dict | None:
    """获取用户信息，需鉴权。"""
    role = authenticate(token)
    if not check_permission(role, "read"):
        return None

    cached = cache_get(f"user:{user_id}")
    if cached is not None:
        return cached

    users = db_fetch("users")
    for u in users:
        if u["id"] == user_id:
            cache_set(f"user:{user_id}", u)
            return u
    return None


def get_all_products(token: str) -> list[dict]:
    """获取所有产品。"""
    role = authenticate(token)
    if not check_permission(role, "read"):
        return []
    return db_fetch("products")
