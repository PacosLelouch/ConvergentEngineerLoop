"""通知服务 —— T02 涉及。"""

import logging

logger = logging.getLogger(__name__)


def send_receipt(user_email: str, amount: float) -> bool:
    """发送支付收据邮件。

    Returns:
        True 表示发送成功。
    """
    logger.info("向 %s 发送收据，金额 %.2f", user_email, amount)
    # 模拟发送
    return True
