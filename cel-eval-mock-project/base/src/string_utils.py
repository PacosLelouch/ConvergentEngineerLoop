"""字符串工具 —— T06 涉及。"""


def truncate(text: str | None, max_len: int) -> str:
    """截断文本到指定长度，超过时添加省略号。

    main 分支已正确处理 None、负数、多字节字符。
    T06 只缺测试覆盖这几种边界情况，函数本身正确。
    """
    if text is None:
        return ""
    if max_len <= 0:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
