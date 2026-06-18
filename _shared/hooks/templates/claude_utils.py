# 由 sync-platforms.py 自动生成，修改请改 _shared/hooks/templates/ 下的真源
"""Claude Code 平台的 Hook 输出格式适配器。"""

import json
import os
import sys


def _wrap(decision, reason="", hook_event="PreToolUse"):
    """Claude Code 的 hook 输出需要 hookSpecificOutput 包装。"""
    result = {
        "hookSpecificOutput": {
            "hookEventName": hook_event,
            "permissionDecision": decision
        }
    }
    if reason:
        result["hookSpecificOutput"]["permissionDecisionReason"] = reason
    return result


def format_deny(reason):
    """生成 Claude Code deny 响应。"""
    return _wrap("deny", reason)


def format_allow(reason=""):
    """生成 Claude Code allow 响应。"""
    return _wrap("allow", reason)


def format_ask(reason):
    """生成 Claude Code ask 响应（请求用户确认）。"""
    return _wrap("ask", reason)


def format_additional_context(context):
    """生成 Claude Code systemMessage 响应（注入上下文但不阻止）。

    Claude Code 通过 systemMessage 字段注入额外上下文。
    """
    return {
        "systemMessage": context,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "permissionDecision": "allow"
        }
    }


# 状态文件路径
STATE_FILE = os.path.join(
    os.environ.get('CLAUDE_PROJECT_DIR', '.'), '.claude', 'cel-state.json'
)


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
