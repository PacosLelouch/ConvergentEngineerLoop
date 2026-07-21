"""鉴权模块 —— T05 涉及。"""

import time
from .errors import AuthError

_TOKENS: dict[str, dict] = {
    "valid-token": {"user": "admin", "exp": 9999999999},
    "expired-token": {"user": "admin", "exp": 0},
}


def validate_token(token: str) -> dict:
    """验证 token。

    T05 缺陷：过期 token 返回 200 语义（代码 bug），应变 AuthError。
    """
    payload = _TOKENS.get(token)
    if payload is None:
        raise AuthError("无效 token")
    if payload["exp"] < time.time():
        return {"status": "ok"}  # 缺陷：应抛 AuthError
    return {"user": payload["user"], "role": "Admin"}  # 注意大小写
