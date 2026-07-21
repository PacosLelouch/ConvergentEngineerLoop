"""支付服务 —— T02 涉及。"""

import logging
from .notification import send_receipt

logger = logging.getLogger(__name__)

# 模拟用户邮箱
_USER_EMAILS = {1: "alice@test.com", 2: "bob@test.com"}


def process_payment(user_id: int, amount: float) -> dict:
    """处理支付，成功后发送收据。

    main 分支已正确传递 user_email。
    T02 测试分支会在此引入缺陷（调用 send_receipt 时缺少 user_email 参数）。
    """
    # 模拟扣款
    logger.info("用户 %d 支付 %.2f", user_id, amount)

    # 发送收据
    user_email = _USER_EMAILS.get(user_id, "unknown@test.com")
    try:
        send_receipt(user_email, amount)
    except Exception as e:
        # 收据发送失败不应回滚支付
        logger.error("收据发送失败: %s", e)

    return {"status": "success", "user_id": user_id, "amount": amount}
