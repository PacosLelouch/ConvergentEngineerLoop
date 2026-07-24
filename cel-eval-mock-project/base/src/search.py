"""搜索工具模块 —— T16 涉及。

提供各种搜索算法，当前使用迭代实现以避免递归深度限制。
"""


def full_text_search(query: str, documents: list[str]) -> list[str]:
    """在文档集合中搜索包含查询词的所有文档。

    使用迭代实现，支持任意大小的文档集合。

    Args:
        query: 搜索关键词（多词空格分隔，AND 逻辑）
        documents: 文档内容列表

    Returns:
        包含所有查询词的文档列表（保持原始顺序）
    """
    if not documents:
        return []

    if not query.strip():
        return []

    query_terms = query.lower().split()
    results = []

    for doc in documents:
        doc_lower = doc.lower()
        # 迭代检查所有查询词
        all_match = True
        for term in query_terms:
            if term not in doc_lower:
                all_match = False
                break
        if all_match:
            results.append(doc)

    return results


def search_with_filters(
    query: str,
    documents: list[str],
    max_results: int = 100,
) -> list[str]:
    """搜索并限制最大结果数（迭代实现）。

    Args:
        query: 搜索关键词
        documents: 文档列表
        max_results: 最大返回结果数

    Returns:
        最多 max_results 条匹配文档
    """
    results = full_text_search(query, documents)
    return results[:max_results]
