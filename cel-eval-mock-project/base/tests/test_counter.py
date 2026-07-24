"""线程安全计数器测试 —— T17 涉及。

包含单线程测试、并发压力测试和同步机制验证。
"""

import threading
import inspect
from src.counter import ThreadSafeCounter


# ── 同步机制验证（确定性测试） ──

def test_uses_synchronization():
    """ThreadSafeCounter 必须使用同步原语（如 threading.Lock）。

    此测试通过检查实例属性确保确实添加了锁机制，
    而非仅仅依赖并发测试的随机失败。

    注意：threading.Lock 在 Python 中是 builtin_function，不是 class，
    因此需要取其实例的类型进行 isinstance 检查。
    """
    counter = ThreadSafeCounter()

    # 获取实际锁类型（threading.Lock 是函数，取其实例的类型）
    _lock_type = type(threading.Lock())       # _thread.lock
    _rlock_type = type(threading.RLock())      # _thread.RLock
    _sync_types = (_lock_type, _rlock_type, threading.Semaphore)

    # 检查实例属性
    has_lock = False
    for name, value in inspect.getmembers(counter):
        if isinstance(value, _sync_types):
            has_lock = True
            break

    # 也检查通过 dir() 能访问到的属性
    if not has_lock:
        for name in dir(counter):
            attr = getattr(counter, name, None)
            if isinstance(attr, _sync_types):
                has_lock = True
                break

    assert has_lock, (
        "ThreadSafeCounter 必须使用同步原语（threading.Lock 等）"
        "以确保线程安全。当前实现中未检测到锁。"
    )


# ── 单线程测试（5 个） ──

def test_initial_value():
    """初始值应为构造参数值。"""
    c = ThreadSafeCounter(10)
    assert c.get() == 10


def test_default_initial_value():
    """默认初始值应为 0。"""
    c = ThreadSafeCounter()
    assert c.get() == 0


def test_increment():
    """increment 应每次 +1 并返回新值。"""
    c = ThreadSafeCounter()
    assert c.increment() == 1
    assert c.increment() == 2
    assert c.get() == 2


def test_increment_by():
    """increment_by 应按 delta 改变计数。"""
    c = ThreadSafeCounter(5)
    result = c.increment_by(10)
    assert result == 15
    assert c.get() == 15


def test_reset():
    """reset 应将计数值归零。"""
    c = ThreadSafeCounter(42)
    c.reset()
    assert c.get() == 0


# ── 并发测试（2 个） ──

def test_concurrent_increment():
    """并发 increment 应精确计数（30 线程，每线程 2000 次）。"""
    counter = ThreadSafeCounter()
    num_threads = 30
    increments_per_thread = 2000

    def worker():
        for _ in range(increments_per_thread):
            counter.increment()

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter.get() == num_threads * increments_per_thread


def test_concurrent_mixed_ops():
    """并发混合操作（increment + increment_by）应精确计数。"""
    counter = ThreadSafeCounter()
    num_threads = 20
    ops_per_thread = 2000

    def worker():
        for i in range(ops_per_thread):
            if i % 2 == 0:
                counter.increment()
            else:
                counter.increment_by(2)

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 每线程：1000 次 +1, 1000 次 +2 = 1000*1 + 1000*2 = 3000
    expected = num_threads * 3000
    assert counter.get() == expected


# ── 并发压力测试 ──

def test_concurrent_stress():
    """高并发压力测试（50 线程，5000 次操作）。"""
    counter = ThreadSafeCounter()
    num_threads = 50
    ops_per_thread = 5000

    def worker():
        for _ in range(ops_per_thread):
            counter.increment()

    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter.get() == num_threads * ops_per_thread
