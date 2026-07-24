"""线程安全计数器模块 —— T17 涉及。

提供线程安全的计数器实现，使用细粒度锁保护共享状态。
"""

import threading


class ThreadSafeCounter:
    """线程安全的计数器。

    使用 threading.Lock 保护所有读写操作，确保并发场景下计数准确。
    锁粒度：方法级别，每个公开方法加锁保护。
    """

    def __init__(self, initial: int = 0) -> None:
        self._value = initial
        self._lock = threading.Lock()

    def increment(self) -> int:
        """计数 +1，返回新值。"""
        with self._lock:
            self._value += 1
            return self._value

    def get(self) -> int:
        """返回当前计数值。"""
        with self._lock:
            return self._value

    def increment_by(self, delta: int) -> int:
        """计数 +delta，返回新值。

        Args:
            delta: 增加量（可为负数表示减少）
        """
        with self._lock:
            self._value += delta
            return self._value

    def reset(self) -> None:
        """重置计数为 0。"""
        with self._lock:
            self._value = 0
