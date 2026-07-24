"""配置验证模块 —— T18 涉及。

⚠️ 已知缺陷：假设 config 非空，对空字典调用时抛出 KeyError 而非 ValidationError。
"""


class ValidationError(Exception):
    """配置验证错误。"""

    pass


_REQUIRED_FIELDS: dict[str, type] = {
    "name": str,
    "version": str,
    "port": int,
}


def validate(config: dict) -> bool:
    """验证配置字典。

    Args:
        config: parse_config 返回的配置字典

    Returns:
        验证通过返回 True

    Raises:
        ValidationError: 缺少必需字段或类型不匹配时
    """
    if not isinstance(config, dict):
        raise ValidationError(f"配置必须是字典，而不是 {type(config).__name__}")

    # ← 缺陷：直接用 [] 访问，空字典时抛 KeyError 而非 ValidationError
    for field, expected_type in _REQUIRED_FIELDS.items():
        value = config[field]  # ← KeyError on empty dict
        if not isinstance(value, expected_type):
            actual = type(value).__name__
            raise ValidationError(
                f"字段 '{field}' 类型错误: 期望 {expected_type.__name__}, "
                f"实际 {actual}"
            )

    return True
