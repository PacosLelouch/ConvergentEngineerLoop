"""API 模块 —— T08 涉及。"""

from dataclasses import dataclass


@dataclass
class QueryRequest:
    table: str
    filters: dict | None = None


def list_users() -> dict:
    """列出所有用户。"""
    return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "total": 2}


def get_user(user_id: int) -> dict:
    """按 ID 获取用户。

    main 分支已做输入校验。
    T08 测试分支缺少校验（SQL 注入风险）。
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("无效的 user_id")
    return {"id": user_id, "name": f"User{user_id}"}


def query_table(request: QueryRequest) -> dict:
    """查询表数据。

    main 分支已校验 table 名。
    T08 测试分支缺少校验（SQL 注入风险）。
    """
    allowed_tables = {"users", "orders", "products"}
    if request.table not in allowed_tables:
        raise ValueError(f"不允许查询表: {request.table}")
    return {"table": request.table, "rows": 0}
