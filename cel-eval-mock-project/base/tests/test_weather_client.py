"""天气 API 客户端测试 —— T20 涉及。

基于真实 API 响应格式的测试（非文档描述的错误扁平格式）。
"""

import pytest
from src.weather_client import get_weather, WeatherData


def test_get_weather_normal_response():
    """正常响应应正确解析温度和湿度。"""
    response = {"main": {"temp": 22.5}, "humidity": 65}
    result = get_weather(response)
    assert isinstance(result, WeatherData)
    assert result.temperature == 22.5
    assert result.humidity == 65


def test_get_weather_zero_temp():
    """温度为 0 时应正确返回。"""
    response = {"main": {"temp": 0.0}, "humidity": 50}
    result = get_weather(response)
    assert result.temperature == 0.0


def test_get_weather_negative_temp():
    """负温度应正确解析。"""
    response = {"main": {"temp": -15.0}, "humidity": 80}
    result = get_weather(response)
    assert result.temperature == -15.0


def test_get_weather_missing_humidity():
    """缺少 humidity 字段应使用默认值 0，不崩溃。"""
    response = {"main": {"temp": 20.0}}
    result = get_weather(response)
    assert result.temperature == 20.0
    assert result.humidity == 0


def test_get_weather_missing_main():
    """缺少 main 字段时应使用默认温度 0，不崩溃。"""
    response = {"humidity": 70}
    result = get_weather(response)
    assert result.temperature == 0.0
    assert result.humidity == 70


def test_get_weather_error_response():
    """错误响应应抛出 ValueError。"""
    response = {"error": "city not found"}
    with pytest.raises(ValueError, match="city not found"):
        get_weather(response)


def test_get_weather_non_dict():
    """非字典输入应抛出 TypeError。"""
    with pytest.raises(TypeError):
        get_weather("not a dict")
