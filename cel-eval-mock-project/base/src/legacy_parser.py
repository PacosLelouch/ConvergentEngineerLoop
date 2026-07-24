"""遗留日志解析器 —— T19 涉及。

解析应用日志文件，支持文件路径模式和流式输入模式。
重构后支持两种调用方式，保持向后兼容。
"""

import re
from typing import Iterator, Iterable
from dataclasses import dataclass

# 时间戳正则（ISO 8601 格式：2024-01-15T10:30:45）
_TIMESTAMP_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+"
    r"(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+"
    r"(.+)$"
)

# 支持的日志级别
_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

# 最大行长度（防止单行过大占用内存）
_MAX_LINE_LENGTH = 8192


@dataclass
class LogEntry:
    """单条日志记录。"""

    timestamp: str
    level: str
    message: str


def parse(source: str | Iterable[str], streaming: bool = False):
    """解析日志，支持文件和流式两种模式。

    Args:
        source: 文件路径（str）或日志行迭代器（Iterable[str]）
        streaming: 是否使用流式模式。
                   False 时 source 为文件路径，返回 List[LogEntry]
                   True 时 source 为 Iterable[str]，返回 Iterator[LogEntry]

    Returns:
        List[LogEntry] 或 Iterator[LogEntry]，取决于 streaming 参数

    Raises:
        FileNotFoundError: streaming=False 且文件不存在
        ValueError: 日志格式无效
    """
    if not streaming:
        # 文件路径模式（向后兼容旧接口）
        if not isinstance(source, str):
            raise TypeError(
                f"streaming=False 时期望 source 为文件路径(str)，"
                f"实际为 {type(source).__name__}"
            )
        return _parse_from_file(source)
    else:
        # 流式输入模式
        if isinstance(source, str):
            raise TypeError(
                "streaming=True 时期望 source 为 Iterable[str]，"
                "实际为 str（提示：使用 streaming=False 读取文件）"
            )
        return _parse_stream(source)


def _parse_from_file(file_path: str) -> list[LogEntry]:
    """从文件读取并解析所有日志行。

    Args:
        file_path: 日志文件路径

    Returns:
        解析后的 LogEntry 列表
    """
    entries: list[LogEntry] = []
    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.rstrip("\n\r")
            if not line:
                continue
            entry = _parse_line(line, line_num)
            entries.append(entry)
    return entries


def _parse_stream(lines: Iterable[str]) -> Iterator[LogEntry]:
    """流式解析日志行。

    逐行读取并逐条 yield，适合大文件或实时日志。

    Args:
        lines: 日志行迭代器

    Yields:
        逐条 LogEntry
    """
    for line_num, line in enumerate(lines, start=1):
        line = line.rstrip("\n\r")
        if not line:
            continue
        yield _parse_line(line, line_num)


def _parse_line(line: str, line_num: int) -> LogEntry:
    """解析单行日志。

    Args:
        line: 单行日志文本
        line_num: 行号（用于错误信息）

    Returns:
        LogEntry 实例

    Raises:
        ValueError: 行格式无法解析
    """
    if len(line) > _MAX_LINE_LENGTH:
        raise ValueError(
            f"第 {line_num} 行超过最大长度限制 "
            f"({len(line)} > {_MAX_LINE_LENGTH})"
        )

    match = _TIMESTAMP_PATTERN.match(line)
    if not match:
        raise ValueError(
            f"第 {line_num} 行格式无效: '{line[:80]}...'"
        )

    timestamp = match.group(1)
    level = match.group(2)

    if level not in _LOG_LEVELS:
        raise ValueError(
            f"第 {line_num} 行日志级别无效: '{level}'"
        )

    message = match.group(3)
    return LogEntry(timestamp=timestamp, level=level, message=message)
