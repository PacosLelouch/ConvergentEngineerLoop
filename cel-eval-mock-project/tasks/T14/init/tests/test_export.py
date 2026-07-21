"""T14 导出测试 —— init 分支 test_export_csv_empty_data 失败。"""

from src.export import export_csv


def test_export_csv_basic():
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    result = export_csv(data)
    assert "name,age" in result


def test_export_csv_empty_data():
    """init：空数据时 export_csv 崩溃（IndexError）。"""
    result = export_csv([])
    assert result == ""

# 缺失测试：特殊字符处理
