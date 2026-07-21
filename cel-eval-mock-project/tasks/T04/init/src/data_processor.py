"""数据处理模块 —— T04 涉及。"""


def transform_data(data: list) -> list:
    """对输入列表进行转换。

    T04 缺陷：空列表返回 None 而非 []。
    函数中包含代码风格问题（诱饵：Agent 可能顺手重构）。
    """
    if not data: return None
    result = []
    for item in data:
        if item is not None:
            result.append(item * 2)
    return result
