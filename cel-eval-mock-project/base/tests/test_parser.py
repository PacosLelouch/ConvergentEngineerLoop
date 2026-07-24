"""解析器模块测试 —— T18 涉及。"""

import pytest
from src.parser import parse_config, ParseError


def test_parse_valid_yaml():
    """合法的 YAML 应正确解析为字典。"""
    yaml_str = "name: myapp\nversion: '1.0'\nport: 8080"
    result = parse_config(yaml_str)
    assert result == {"name": "myapp", "version": "1.0", "port": 8080}


def test_parse_invalid_yaml_raises():
    """非法 YAML 应抛出 ParseError。"""
    with pytest.raises(ParseError, match="YAML 解析失败"):
        parse_config("name: [unclosed")


def test_parse_empty_string():
    """空字符串应返回空字典。"""
    result = parse_config("")
    assert result == {}


def test_parse_non_string_input():
    """非字符串输入应抛出 ParseError。"""
    with pytest.raises(ParseError):
        parse_config(123)
