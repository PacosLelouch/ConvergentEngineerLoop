# 由 sync-platforms.py 自动生成，修改请改 _shared/hooks/templates/ 下的真源
"""Codex 平台的 Hook 输出格式适配器。"""

import json
import os
import sys


def format_deny(reason):
    """生成 Codex deny 响应。"""
    return {"permissionDecision": "deny", "reason": reason}


def format_allow(reason=""):
    """生成 Codex allow 响应。"""
    result = {"permissionDecision": "allow"}
    if reason:
        result["reason"] = reason
    return result


def format_ask(reason):
    """生成 Codex ask 响应。

    Codex 不支持 ask 决策，降级为 deny 并标注需用户确认。
    """
    return {"permissionDecision": "deny", "reason": f"[需用户确认] {reason}"}


def format_additional_context(context):
    """生成 Codex additionalContext 响应（注入上下文但不阻止）。"""
    return {"additionalContext": context}


# 状态文件路径
STATE_FILE = os.path.join(os.getcwd(), '.codex', 'cel-state.json')


def output(result):
    """输出 JSON 结果到 stdout 并退出。"""
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


def load_state():
    """加载 CEL 状态文件。"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": 1, "task": {}, "current_iteration": 0, "iterations": []}


def save_state(state):
    """保存 CEL 状态文件。"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
