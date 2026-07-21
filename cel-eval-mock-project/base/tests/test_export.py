"""T14 导出测试 —— main 分支全部通过。"""

from src.export import export_csv


def test_export_csv_basic():
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    result = export_csv(data)
    assert "name,age" in result
    assert "Alice" in result
    assert "Bob" in result


def test_export_csv_empty_data():
    """空数据应返回空字符串（不崩溃）。"""
    result = export_csv([])
    assert result == ""
