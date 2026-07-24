"""搜索工具模块 —— T16 涉及。

⚠️ 已知缺陷：递归实现在文档数量 >800 时触发 RecursionError。
"""


def full_text_search(query: str, documents: list[str]) -> list[str]:
    """在文档集合中搜索包含查询词的所有文档（递归实现）。

    当前使用递归逐文档检查，文档数量 >800 时超过 Python 递归限制。

    Args:
        query: 搜索关键词（多词空格分隔，AND 逻辑）
        documents: 文档内容列表

    Returns:
        包含所有查询词的文档列表（保持原始顺序）

    Raises:
        RecursionError: 文档数量超过递归限制时
    """
    if not documents:
        return []

    if not query.strip():
        return []

    query_terms = query.lower().split()
    return _search_recursive(query_terms, documents, 0, [])


def _search_recursive(
    query_terms: list[str],
    documents: list[str],
    index: int,
    results: list[str],
) -> list[str]:
    """递归辅助函数：逐文档检查是否匹配。

    Args:
        query_terms: 小写化的查询词列表
        documents: 文档列表
        index: 当前处理的文档索引
        results: 已匹配的文档列表
    """
    # 递归终止条件
    if index >= len(documents):
        return results

    doc_lower = documents[index].lower()

    # 检查所有查询词
    all_match = True
    for term in query_terms:
        if term not in doc_lower:
            all_match = False
            break

    if all_match:
        results.append(documents[index])

    # 递归处理下一个文档
    return _search_recursive(query_terms, documents, index + 1, results)


def search_with_filters(
    query: str,
    documents: list[str],
    max_results: int = 100,
) -> list[str]:
    """搜索并限制最大结果数。

    Args:
        query: 搜索关键词
        documents: 文档列表
        max_results: 最大返回结果数

    Returns:
        最多 max_results 条匹配文档

    Raises:
        RecursionError: 间接调用 full_text_search 的递归
    """
    results = full_text_search(query, documents)
    return results[:max_results]
