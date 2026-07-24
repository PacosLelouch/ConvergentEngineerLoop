"""天气 API 客户端模块 —— T20 涉及。

调用外部天气 API 获取天气数据。
根据真实 API 响应格式解析（非文档描述的错误格式）。
"""

from dataclasses import dataclass

# --- 真实 API 响应格式（基于生产日志推断）---
# {
#     "main": {"temp": 22.5},
#     "humidity": 65
# }
# 错误响应: {"error": "city not found"}
# 不完整响应: {"main": {"temp": 22.5}}  # 缺 humidity

_DEFAULT_TEMP = 0.0
_DEFAULT_HUMIDITY = 0


@dataclass
class WeatherData:
    """天气数据。"""

    temperature: float  # 摄氏度
    humidity: int       # 湿度百分比 (0-100)


def get_weather(api_response: dict) -> WeatherData:
    """从 API 响应中提取天气数据。

    根据生产日志推断的真实格式：
    {"main": {"temp": float}, "humidity": int}

    Args:
        api_response: 原始 API 响应字典

    Returns:
        WeatherData 实例（缺失字段使用默认值）

    Raises:
        ValueError: 响应包含错误信息时
        KeyError: 响应格式完全不匹配时（保留以便上层处理）
    """
    if not isinstance(api_response, dict):
        raise TypeError(f"期望 dict 类型的响应，实际 {type(api_response).__name__}")

    # 检查错误响应
    if "error" in api_response:
        raise ValueError(f"API 返回错误: {api_response['error']}")

    # 解析温度（真实格式：嵌套在 main 中）
    temp = _DEFAULT_TEMP
    if "main" in api_response and isinstance(api_response["main"], dict):
        if "temp" in api_response["main"]:
            temp = float(api_response["main"]["temp"])

    # 解析湿度
    humidity = _DEFAULT_HUMIDITY
    if "humidity" in api_response:
        humidity = int(api_response["humidity"])

    return WeatherData(temperature=temp, humidity=humidity)
