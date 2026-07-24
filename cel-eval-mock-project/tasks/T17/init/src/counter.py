"""计数器模块 —— T17 涉及。

⚠️ 已知缺陷：类名虽为 ThreadSafeCounter，但缺少同步机制。
increment() 使用显式的"读取-修改-写入"三步操作，
在并发场景下容易因 GIL 切换导致计数丢失。
"""


class ThreadSafeCounter:
    """计数器（非线程安全 — 缺少同步机制）。

    当前 increment() 实现为显式的三步操作：
    1. 读取当前值
    2. 计算新值
    3. 写回新值
    多线程并发时，两步之间可能发生 GIL 切换，导致计数丢失。
    """

    def __init__(self, initial: int = 0) -> None:
        self._value = initial

    def increment(self) -> int:
        """计数 +1，返回新值（三步非原子操作，竞态条件高发）。"""
        v = self._value  # 步骤 1：读
        v = v + 1        # 步骤 2：改
        self._value = v  # 步骤 3：写（竞态窗口）
        return v

    def get(self) -> int:
        """返回当前计数值。"""
        return self._value

    def increment_by(self, delta: int) -> int:
        """计数 +delta，返回新值（三步非原子操作，竞态条件高发）。

        Args:
            delta: 增加量（可为负数表示减少）
        """
        v = self._value
        v = v + delta
        self._value = v
        return v

    def reset(self) -> None:
        """重置计数为 0。"""
        self._value = 0
