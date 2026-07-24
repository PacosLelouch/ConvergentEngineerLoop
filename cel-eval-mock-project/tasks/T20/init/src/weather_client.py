"""天气 API 客户端模块 —— T20 涉及。

调用外部天气 API 获取天气数据。
基于 API 文档描述的格式（⚠️ 与生产日志不符）。
"""

from dataclasses import dataclass

# 根据 API 文档，响应为扁平结构：
# {"temp": 22.5, "humidity": 65}


@dataclass
class WeatherData:
    """天气数据。"""

    temperature: float
    humidity: int


def get_weather(api_response: dict) -> WeatherData:
    """从 API 响应中提取天气数据。

    根据 API 文档，格式为：
    {"temp": float, "humidity": int}

    Args:
        api_response: 原始 API 响应字典

    Returns:
        WeatherData 实例

    Raises:
        KeyError: 缺少必需字段时
    """
    # 直接按文档格式取字段（缺少错误响应和不完整响应处理）
    temp = api_response["temp"]
    humidity = api_response["humidity"]

    return WeatherData(temperature=float(temp), humidity=int(humidity))
