"""查询构建模块 —— T07 涉及（级联错误链中的一环）。"""

import logging

logger = logging.getLogger(__name__)


def build_query(table: str, filters: dict | None = None) -> str:
    """构建 SQL 查询。"""
    query = f"SELECT * FROM {table}"
    if filters:
        conditions = " AND ".join(f"{k} = %s" for k in filters)
        query += f" WHERE {conditions}"
    return query
