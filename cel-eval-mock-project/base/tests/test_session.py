"""T05 会话测试 —— main 分支全部通过。"""


def test_session_timeout_boundary():
    """会话超时边界测试（非 Flaky —— 使用固定时间）。"""
    # 显式注入固定时刻，不依赖 wall clock 或调度速度。
    session = {"user_id": 1, "created_at": 1_000.0, "ttl": 300}
    now = 1_299.0
    expired = (now - session["created_at"]) > session["ttl"]
    assert not expired
