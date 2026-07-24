"""遗留日志解析器测试 —— T19 涉及。

包含 15 个旧测试（兼容旧接口）和 5 个流式模式新测试。
"""

import os
import tempfile
import pytest
from src.legacy_parser import parse, LogEntry

# ── 测试用日志数据 ──

_SAMPLE_LOG = """2024-01-15T10:30:45 INFO Server started on port 8080
2024-01-15T10:30:46 DEBUG Loading configuration from config.yaml
2024-01-15T10:30:47 WARNING Disk usage above 80%
2024-01-15T10:31:00 ERROR Connection to database failed
2024-01-15T10:31:05 CRITICAL Out of memory
"""


def _write_temp_log(content: str) -> str:
    """写入临时日志文件，返回路径。"""
    fd, path = tempfile.mkstemp(suffix=".log", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ── 旧测试：文件路径模式（15 个） ──

def test_parse_file_all_entries():
    """应正确解析所有日志条目。"""
    path = _write_temp_log(_SAMPLE_LOG)
    try:
        entries = parse(path)
        assert len(entries) == 5
    finally:
        os.unlink(path)


def test_parse_file_first_entry():
    """第一条日志应正确解析。"""
    path = _write_temp_log(_SAMPLE_LOG)
    try:
        entries = parse(path)
        first = entries[0]
        assert first.timestamp == "2024-01-15T10:30:45"
        assert first.level == "INFO"
        assert first.message == "Server started on port 8080"
    finally:
        os.unlink(path)


def test_parse_file_last_entry():
    """最后一条日志应正确解析。"""
    path = _write_temp_log(_SAMPLE_LOG)
    try:
        entries = parse(path)
        last = entries[-1]
        assert last.level == "CRITICAL"
        assert last.message == "Out of memory"
    finally:
        os.unlink(path)


def test_parse_file_entry_type():
    """返回的条目应为 LogEntry 实例。"""
    path = _write_temp_log("2024-01-15T10:30:45 INFO Test message")
    try:
        entries = parse(path)
        assert isinstance(entries[0], LogEntry)
    finally:
        os.unlink(path)


def test_parse_file_empty():
    """空文件应返回空列表。"""
    path = _write_temp_log("")
    try:
        entries = parse(path)
        assert entries == []
    finally:
        os.unlink(path)


def test_parse_file_blank_lines():
    """空行应被跳过。"""
    content = "2024-01-15T10:30:45 INFO First\n\n2024-01-15T10:30:46 DEBUG Second\n"
    path = _write_temp_log(content)
    try:
        entries = parse(path)
        assert len(entries) == 2
    finally:
        os.unlink(path)


def test_parse_file_debug_level():
    """DEBUG 级别日志应正确解析。"""
    path = _write_temp_log("2024-01-15T10:30:46 DEBUG Config loaded")
    try:
        entries = parse(path)
        assert entries[0].level == "DEBUG"
    finally:
        os.unlink(path)


def test_parse_file_warning_level():
    """WARNING 级别日志应正确解析。"""
    path = _write_temp_log("2024-01-15T10:30:47 WARNING Low memory")
    try:
        entries = parse(path)
        assert entries[0].level == "WARNING"
    finally:
        os.unlink(path)


def test_parse_file_error_level():
    """ERROR 级别日志应正确解析。"""
    path = _write_temp_log("2024-01-15T10:31:00 ERROR DB timeout")
    try:
        entries = parse(path)
        assert entries[0].level == "ERROR"
    finally:
        os.unlink(path)


def test_parse_file_critical_level():
    """CRITICAL 级别日志应正确解析。"""
    path = _write_temp_log("2024-01-15T10:31:05 CRITICAL System halted")
    try:
        entries = parse(path)
        assert entries[0].level == "CRITICAL"
    finally:
        os.unlink(path)


def test_parse_file_long_message():
    """长消息应正确解析。"""
    msg = "A" * 200
    path = _write_temp_log(f"2024-01-15T10:30:45 INFO {msg}")
    try:
        entries = parse(path)
        assert entries[0].message == msg
    finally:
        os.unlink(path)


def test_parse_file_multiline_content():
    """多行日志条目应各自独立。"""
    path = _write_temp_log(_SAMPLE_LOG)
    try:
        entries = parse(path)
        timestamps = [e.timestamp for e in entries]
        assert timestamps == [
            "2024-01-15T10:30:45",
            "2024-01-15T10:30:46",
            "2024-01-15T10:30:47",
            "2024-01-15T10:31:00",
            "2024-01-15T10:31:05",
        ]
    finally:
        os.unlink(path)


def test_parse_file_invalid_format():
    """无效格式应抛出 ValueError。"""
    path = _write_temp_log("this is not a valid log line")
    try:
        with pytest.raises(ValueError, match="格式无效"):
            parse(path)
    finally:
        os.unlink(path)


def test_parse_file_nonexistent():
    """不存在的文件应抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        parse("/nonexistent/path.log")


def test_parse_file_wrong_type_streaming_false():
    """streaming=False 时传入非 str 应抛 TypeError。"""
    with pytest.raises(TypeError):
        parse(["line1", "line2"], streaming=False)


# ── 新测试：流式模式（5 个） ──

def test_parse_stream_all_entries():
    """流式模式应正确解析所有日志条目。"""
    lines = _SAMPLE_LOG.strip().split("\n")
    results = list(parse(lines, streaming=True))
    assert len(results) == 5


def test_parse_stream_first_entry():
    """流式模式第一条日志应正确解析。"""
    lines = _SAMPLE_LOG.strip().split("\n")
    results = list(parse(lines, streaming=True))
    assert results[0].level == "INFO"
    assert results[0].message == "Server started on port 8080"


def test_parse_stream_type():
    """流式模式返回的条目应为 LogEntry。"""
    lines = ["2024-01-15T10:30:45 INFO Test"]
    results = list(parse(lines, streaming=True))
    assert isinstance(results[0], LogEntry)


def test_parse_stream_empty():
    """流式模式空输入应返回空迭代器。"""
    results = list(parse([], streaming=True))
    assert results == []


def test_parse_stream_wrong_type():
    """streaming=True 时传入 str 应抛 TypeError。"""
    with pytest.raises(TypeError):
        list(parse("/some/file.log", streaming=True))
