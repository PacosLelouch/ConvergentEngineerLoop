"""写入器模块测试 —— T18 涉及。"""

import os
import tempfile
import pytest
from src.writer import write_output
from src.validator import ValidationError


def test_write_output_success():
    """正常写入应成功创建文件。"""
    data = {"name": "myapp", "version": "1.0", "port": 8080}
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "output.txt")
        result = write_output(data, filepath)
        assert result == filepath
        assert os.path.exists(filepath)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        assert "name: myapp" in content


def test_write_output_invalid_data_no_temp_file_leak():
    """验证失败时应清理临时文件，不残留 .tmp 文件。"""
    data = {"name": "myapp"}  # 缺少 version 和 port
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "output.txt")
        with pytest.raises(ValidationError):
            write_output(data, filepath)
        # 确保目标文件未被创建
        assert not os.path.exists(filepath)
        # 确保无 .tmp 文件残留
        tmp_files = [f for f in os.listdir(tmpdir) if f.endswith(".tmp")]
        assert len(tmp_files) == 0, f"残留临时文件: {tmp_files}"
