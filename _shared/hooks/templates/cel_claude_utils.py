"""Claude Code 平台的 CEL Hook 工具模块。

提供：
- 输出格式适配（format_deny/allow/ask/additional_context）
- 状态文件读写（load_state/save_state）
- CEL 激活检查（is_cel_active）
- 平台特定工具名集合（EDIT_TOOLS/COMMAND_TOOLS）
"""

import json
import os
import sys


# Claude Code 工具名（与 Codex 同源，区分大小写）
EDIT_TOOLS = {'Edit', 'Write', 'apply_patch'}

# 命令执行工具名
COMMAND_TOOLS = {'Bash'}


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


def format_deny(reason, event_name="PreToolUse"):
    """生成 Claude Code deny 响应。"""
    return _wrap("deny", reason, event_name)


def format_allow(reason=""):
    """生成 Claude Code allow 响应。"""
    return _wrap("allow", reason)


def format_ask(reason, event_name="PreToolUse"):
    """生成 Claude Code ask 响应（请求用户确认）。"""
    return _wrap("ask", reason, event_name)


def format_additional_context(context, event_name="PostToolUse"):
    """生成 Claude Code systemMessage 响应（注入上下文但不阻止）。

    Claude Code 通过 systemMessage 字段注入额外上下文。
    """
    return {
        "systemMessage": context,
        "hookSpecificOutput": {
            "hookEventName": event_name,
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


def is_cel_active():
    """检查当前是否有 CEL 活跃任务。

    未激活时 hooks 应直接放行，不干扰其他系统。
    判定依据：cel-state.json 中 task.description 非空。
    """
    state = load_state()
    task_desc = state.get('task', {}).get('description', '')
    return bool(task_desc.strip())
