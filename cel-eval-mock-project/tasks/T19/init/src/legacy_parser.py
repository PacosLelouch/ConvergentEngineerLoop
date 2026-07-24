"""遗留日志解析器 —— T19 涉及。

解析应用日志文件。当前仅支持文件路径模式，代码风格陈旧待重构。
"""

import re
import os
from typing import List  # 旧式导入风格

# 旧式常量，缺少类型标注
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+(.+)$")
# Magic number: 最大行长度
ML = 8192


class LogEntry:
    """单条日志记录（旧式普通类，非 dataclass）。"""

    def __init__(self, ts, lv, msg):
        self.timestamp = ts
        self.level = lv
        self.message = msg

    def __repr__(self):
        return f"LogEntry({self.timestamp}, {self.level}, {self.message[:50]})"


def parse(file_path):
    """解析日志文件（仅支持文件路径）。

    Args:
        file_path: 日志文件路径

    Returns:
        LogEntry 列表

    Raises:
        FileNotFoundError: 文件不存在
        RuntimeError: 格式错误（异常类型不统一）
    """
    # 80+ 行的巨型函数 —— 读取、解析、验证全部混在一起
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    all_lines = []
    f = None  # 旧式手动 close 模式
    try:
        f = open(file_path, "r", encoding="utf-8")
        # 一次性全读到内存（大文件会炸）
        for x in f:
            x = x.rstrip("\n").rstrip("\r")  # 两次 rstrip
            if x != "" and x != "\n":  # 多余的空行检查
                all_lines.append(x)
    finally:
        if f:
            f.close()

    # 开始解析（解析逻辑全在一个大循环里）
    entries = []
    for i in range(len(all_lines)):
        ln = all_lines[i]
        ln_num = i + 1

        # 行长度检查
        if len(ln) > 8192:  # ← Magic number，未使用 ML 常量
            raise RuntimeError(f"Line {ln_num} too long: {len(ln)} > 8192")

        # 正则匹配
        m = TS_RE.match(ln)
        if not m:
            # 错误消息不友好，未截断长行
            raise RuntimeError(f"Bad format at line {ln_num}: {ln}")

        ts = m.group(1)
        lv = m.group(2)

        # 日志级别验证使用硬编码列表而非常量
        ok_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if lv not in ok_levels:
            raise RuntimeError(f"Bad level at line {ln_num}: '{lv}'")

        msg = m.group(3)

        # 创建条目
        e = LogEntry(ts, lv, msg)
        entries.append(e)

    return entries
