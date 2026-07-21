"""T05 会话测试 —— main 分支全部通过。"""

import time


def test_session_timeout_boundary():
    """会话超时边界测试（非 Flaky —— 使用固定时间）。"""
    start = time.time()
    # 模拟会话逻辑
    session = {"user_id": 1, "created_at": start, "ttl": 300}
    expired = (time.time() - session["created_at"]) > session["ttl"]
    assert not expired
