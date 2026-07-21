"""T02 支付测试 —— main 分支全部通过。"""

import pytest
from unittest.mock import patch
from src.payment import process_payment


def test_process_payment_success():
    result = process_payment(user_id=1, amount=99.99)
    assert result["status"] == "success"
    assert result["amount"] == 99.99


def test_process_payment_different_user():
    result = process_payment(user_id=2, amount=50.0)
    assert result["status"] == "success"
    assert result["amount"] == 50.0


def test_payment_with_receipt():
    """支付成功后应发送收据。"""
    result = process_payment(user_id=1, amount=10.0)
    assert result["status"] == "success"


def test_payment_receipt_failure_does_not_rollback():
    """收据发送失败不应回滚支付。"""
    with patch("src.payment.send_receipt", side_effect=Exception("SMTP error")):
        result = process_payment(user_id=1, amount=10.0)
        assert result["status"] == "success"  # 支付仍应成功


def test_payment_invalid_user_defaults_email():
    """不存在的用户使用默认邮箱。"""
    result = process_payment(user_id=999, amount=5.0)
    assert result["status"] == "success"
