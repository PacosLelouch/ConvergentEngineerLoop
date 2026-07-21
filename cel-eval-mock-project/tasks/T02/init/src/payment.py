"""支付服务 —— T02 涉及。"""

import logging
from .notification import send_receipt

logger = logging.getLogger(__name__)

_USER_EMAILS = {1: "alice@test.com", 2: "bob@test.com"}


def process_payment(user_id: int, amount: float) -> dict:
    """处理支付。

    T02 缺陷：
    1. 调用 send_receipt 缺少 user_email 参数。
    2. send_receipt 异常未捕获（会传播导致支付假回滚）。
    """
    logger.info("用户 %d 支付 %.2f", user_id, amount)
    send_receipt(amount)
    return {"status": "success", "user_id": user_id, "amount": amount}
