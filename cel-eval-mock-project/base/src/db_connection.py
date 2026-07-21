"""数据库连接模块 —— T07 涉及。"""

import logging
from .db_config import DATABASE_CONFIG

logger = logging.getLogger(__name__)


def connect():
    """建立数据库连接。连接失败时抛 ConnectionError。"""
    try:
        port = DATABASE_CONFIG["port"]
        # 模拟连接检查
        if port != 5432:
            raise ConnectionError(f"Connection refused: port {port} not available")
        logger.info("数据库连接成功: %s:%d", DATABASE_CONFIG["host"], port)
        return {"connected": True, "port": port}
    except Exception as e:
        logger.error("数据库连接失败: %s", e)
        raise
