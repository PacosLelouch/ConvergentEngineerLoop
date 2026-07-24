"""配置验证模块 —— T18 涉及。

验证解析后的配置字典是否包含必需的字段。
"""


class ValidationError(Exception):
    """配置验证错误。"""

    pass


# 必需字段及其期望类型
_REQUIRED_FIELDS: dict[str, type] = {
    "name": str,
    "version": str,
    "port": int,
}


def validate(config: dict) -> bool:
    """验证配置字典是否包含所有必需字段且类型正确。

    Args:
        config: parse_config 返回的配置字典

    Returns:
        验证通过返回 True

    Raises:
        ValidationError: 缺少必需字段或类型不匹配时
    """
    if not isinstance(config, dict):
        raise ValidationError(f"配置必须是字典，而不是 {type(config).__name__}")

    for field, expected_type in _REQUIRED_FIELDS.items():
        if field not in config:
            raise ValidationError(f"缺少必需字段: '{field}'")
        if not isinstance(config[field], expected_type):
            actual = type(config[field]).__name__
            raise ValidationError(
                f"字段 '{field}' 类型错误: 期望 {expected_type.__name__}, "
                f"实际 {actual}"
            )

    return True
