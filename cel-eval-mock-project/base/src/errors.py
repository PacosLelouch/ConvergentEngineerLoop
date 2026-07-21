"""自定义异常。"""


class DivisionByZeroError(Exception):
    """除数为零时抛出。"""
    pass


class UserNotFoundError(Exception):
    """用户不存在时抛出。"""
    pass


class AuthError(Exception):
    """鉴权失败时抛出。"""
    pass
