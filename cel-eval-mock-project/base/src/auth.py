"""鉴权模块 —— T05 涉及。"""

import time
from .errors import AuthError

# 模拟 token 验证（极简 JWT-like）
_TOKENS: dict[str, dict] = {
    "valid-token": {"user": "admin", "exp": 9999999999},
    "expired-token": {"user": "admin", "exp": 0},
}


def validate_token(token: str) -> dict:
    """验证 token，返回 payload。

    main 分支已正确返回 401 语义（抛 AuthError）。
    T05 测试分支过期 token 返回 {"status": "ok"} 200 语义（代码 bug）。
    """
    payload = _TOKENS.get(token)
    if payload is None:
        raise AuthError("无效 token")
    if payload["exp"] < time.time():
        raise AuthError("token 已过期")
    return {"user": payload["user"], "role": "admin"}
