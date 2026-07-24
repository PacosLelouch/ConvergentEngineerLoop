"""配置解析模块 —— T18 涉及。

解析 YAML 格式的配置字符串，返回解析后的字典。
"""

import yaml


class ParseError(Exception):
    """配置解析错误。"""

    pass


def parse_config(yaml_str: str) -> dict:
    """解析 YAML 配置字符串为字典。

    Args:
        yaml_str: YAML 格式的配置字符串

    Returns:
        解析后的配置字典

    Raises:
        ParseError: 当输入不是合法 YAML 时
    """
    if not isinstance(yaml_str, str):
        raise ParseError(f"输入必须是字符串，而不是 {type(yaml_str).__name__}")

    if yaml_str.strip() == "":
        return {}

    try:
        result = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise ParseError(f"YAML 解析失败: {e}") from e

    # 空 YAML 文档或只含注释
    if result is None:
        return {}

    if not isinstance(result, dict):
        raise ParseError(f"YAML 解析结果应为字典，而不是 {type(result).__name__}")

    return result
