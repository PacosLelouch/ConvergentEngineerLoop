# legacy_parser 迁移指南

## 概述

`legacy_parser.py` 已重构，现在支持两种调用模式：
1. **文件路径模式**（向后兼容旧接口）
2. **流式模式**（新增，适用于大文件或实时日志）

## 迁移步骤

### 旧接口

```python
from src.legacy_parser import parse

entries = parse("/path/to/app.log")
# entries: List[LogEntry]
```

### 新接口

```python
from src.legacy_parser import parse

# 方式 1：文件路径模式（与旧接口完全兼容）
entries = parse("/path/to/app.log")
# entries: List[LogEntry]

# 方式 2：流式模式（新增）
with open("/path/to/large.log") as f:
    for entry in parse(f, streaming=True):
        process(entry)
# entry: LogEntry（逐个 yield，内存友好）
```

## 接口签名

```python
def parse(source: str | Iterable[str], streaming: bool = False):
    """
    Args:
        source: 文件路径（streaming=False）或日志行迭代器（streaming=True）
        streaming: 模式切换标志

    Returns:
        List[LogEntry] 或 Iterator[LogEntry]
    """
```

## 注意事项

- **向后兼容**：不传 `streaming` 参数时行为与旧版完全相同
- **流式模式**：传入 `streaming=True` 时需传入 `Iterable[str]`（如文件对象），而非文件路径
- **异常类型**：统一使用 `ValueError`（格式错误）、`TypeError`（参数类型错误）、`FileNotFoundError`
