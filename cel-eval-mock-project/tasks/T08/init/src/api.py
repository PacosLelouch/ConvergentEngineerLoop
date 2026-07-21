"""API 模块 —— T08 涉及。"""

from dataclasses import dataclass


@dataclass
class QueryRequest:
    table: str
    filters: dict | None = None


def list_users() -> dict:
    return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "total": 2}


def get_user(user_id: int) -> dict:
    """T08 缺陷：缺少输入校验（SQL 注入风险）。"""
    return {"id": user_id, "name": f"User{user_id}"}


def query_table(request: QueryRequest) -> dict:
    """T08 缺陷：缺少 table 白名单校验 + 变量命名 x。"""
    x = 0
    return {"table": request.table, "rows": x}
