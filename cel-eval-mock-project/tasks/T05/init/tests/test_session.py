"""T05 会话测试 —— init 分支为 Flaky 测试。"""

import time
import random


def test_session_timeout_boundary():
    """Flaky 测试：依赖 random，偶尔失败。"""
    start = time.time()
    ttl = 300 + random.randint(-10, 10)
    expired = (time.time() - start) > ttl
    assert not expired
