"""搜索工具模块测试 —— T16 涉及。

测试迭代实现能处理大规模文档集合，递归实现会因深度限制而失败。
"""

from src.search import full_text_search, search_with_filters


# ── 正确性测试（小规模） ──

def test_search_single_term():
    """单个词搜索应返回包含该词的文档。"""
    docs = ["hello world", "hello python", "goodbye world"]
    results = full_text_search("hello", docs)
    assert results == ["hello world", "hello python"]


def test_search_multi_term_and():
    """多词搜索应为 AND 逻辑。"""
    docs = ["hello world", "hello python", "goodbye world"]
    results = full_text_search("hello world", docs)
    assert results == ["hello world"]


def test_search_case_insensitive():
    """搜索应不区分大小写。"""
    docs = ["Hello World", "HELLO Python", "goodbye"]
    results = full_text_search("hello", docs)
    assert results == ["Hello World", "HELLO Python"]


def test_search_no_match():
    """无匹配时应返回空列表。"""
    docs = ["hello world", "hello python"]
    results = full_text_search("xyz", docs)
    assert results == []


def test_search_empty_docs():
    """空文档列表应返回空列表。"""
    results = full_text_search("hello", [])
    assert results == []


def test_search_preserves_order():
    """搜索结果应保持原始文档顺序。"""
    docs = ["a b c", "c d e", "a c f", "b d f"]
    results = full_text_search("a", docs)
    assert results == ["a b c", "a c f"]


# ── 大规模文档测试（递归版会触发 RecursionError） ──

def test_large_document_set_1000():
    """1000 文档搜索应成功完成（递归版上限 ~800）。"""
    docs = [f"document number {i} contains this text" for i in range(1000)]
    # 所有文档都包含 "document"
    results = full_text_search("document", docs)
    assert len(results) == 1000


def test_large_document_set_3000():
    """3000 文档搜索应成功完成。"""
    docs = [f"item_{i} sample content for search" for i in range(3000)]
    # 搜索一个在所有文档中都出现的关键词
    results = full_text_search("sample", docs)
    assert len(results) == 3000


# ── search_with_filters 测试 ──

def test_search_with_filters_limit():
    """max_results 应正确限制返回数量。"""
    docs = [f"doc_{i} common_word extra_{i}" for i in range(50)]
    results = search_with_filters("common_word", docs, max_results=10)
    assert len(results) == 10


def test_search_with_filters_default():
    """默认 max_results=100。"""
    docs = [f"doc_{i} keyword extra_{i}" for i in range(200)]
    results = search_with_filters("keyword", docs)
    assert len(results) == 100
