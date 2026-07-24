"""验证器模块测试 —— T18 涉及。"""

import pytest
from src.validator import validate, ValidationError


def test_validate_valid_config():
    """合法配置应验证通过。"""
    config = {"name": "myapp", "version": "1.0", "port": 8080}
    assert validate(config) is True


def test_validate_missing_field():
    """缺少必需字段应抛出 ValidationError。"""
    config = {"name": "myapp", "version": "1.0"}
    with pytest.raises(ValidationError, match="缺少必需字段"):
        validate(config)


def test_validate_wrong_type():
    """字段类型错误应抛出 ValidationError。"""
    config = {"name": "myapp", "version": "1.0", "port": "not_a_number"}
    with pytest.raises(ValidationError, match="类型错误"):
        validate(config)


def test_validate_empty_dict():
    """空字典应抛出缺少字段的 ValidationError（而非 KeyError）。"""
    with pytest.raises(ValidationError, match="缺少必需字段"):
        validate({})
