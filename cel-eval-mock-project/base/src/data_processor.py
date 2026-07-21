"""数据处理模块 —— T04 涉及。"""


def transform_data(data: list) -> list:
    """对输入列表进行转换。

    main 分支已正确处理空列表（返回 []）。
    T04 测试分支空列表时返回 None（而非 []）。
    """
    if not data:
        return []
    return [item * 2 for item in data if item is not None]
