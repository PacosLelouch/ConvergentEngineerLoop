"""API 处理模块 —— T07 涉及（级联错误链中的一环）。"""

import logging
from .db_connection import connect
from .query_builder import build_query

logger = logging.getLogger(__name__)


def handle_request(endpoint: str, params: dict | None = None) -> dict:
    """处理 API 请求。调用数据库查询。"""
    try:
        conn = connect()
        query = build_query(endpoint, params)
        # 模拟执行查询
        return {"status": "ok", "query": query, "rows": 0}
    except Exception as e:
        logger.error("请求处理失败: %s", e)
        return {"status": "error", "detail": str(e)}
