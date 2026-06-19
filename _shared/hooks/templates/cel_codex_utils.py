"""Codex 平台的 CEL Hook 工具模块。

提供：
- 输出格式适配（format_deny/allow/ask/additional_context）
- 状态文件读写（load_state/save_state）
- CEL 激活检查（is_cel_active）
- 平台特定工具名集合（EDIT_TOOLS/COMMAND_TOOLS）

Codex Hook 输出格式规范：
- PreToolUse deny: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}
- PreToolUse allow + 上下文: {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "..."}}
- PostToolUse 上下文: {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}
- 旧版格式也可用: {"decision": "block", "reason": "..."} 或 exit code 2 + stderr

Codex 工具名规范：
- 文件修改：Edit, Write, apply_patch（Edit|Write 可匹配 apply_patch）
- 命令执行：Bash
- 工具输入：Bash 的命令在 tool_input.command，apply_patch 的内容在 tool_input
"""

import json
import os
import sys


# Codex 工具名（官方规范，区分大小写）
EDIT_TOOLS = {'Edit', 'Write', 'apply_patch'}

# 命令执行工具名
COMMAND_TOOLS = {'Bash'}


def format_deny(reason, event_name="PreToolUse"):
    """生成 Codex deny 响应。"""
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def format_allow(reason=""):
    """生成 Codex allow 响应（默认不输出任何内容即可放行）。"""
    # Codex: 退出码 0 且无输出 = 成功放行
    # 但为了与其他平台统一，仍输出一个空 JSON
    return {}


def format_ask(reason, event_name="PreToolUse"):
    """生成 Codex ask 响应。

    Codex 不支持 ask 决策，降级为 deny 并标注需用户确认。
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[需用户确认] {reason}",
        }
    }


def format_additional_context(context, event_name="PostToolUse"):
    """生成 Codex additionalContext 响应（注入上下文但不阻止）。"""
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": context,
        }
    }


# 状态文件路径：使用脚本所在目录的上级 .codex 目录
# Codex hook 以会话 cwd 运行，但 __file__ 更可靠
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_SCRIPT_DIR, '..', 'cel-state.json')


def output(result):
    """输出 JSON 结果到 stdout 并退出。"""
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


def load_state():
    """加载 CEL 状态文件。"""
    state_path = os.path.normpath(STATE_FILE)
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"version": 1, "task": {}, "current_iteration": 0, "iterations": []}


def save_state(state):
    """保存 CEL 状态文件。"""
    state_path = os.path.normpath(STATE_FILE)
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_cel_active():
    """检查当前是否有 CEL 活跃任务。

    未激活时 hooks 应直接放行，不干扰其他系统。
    判定依据：cel-state.json 中 task.description 非空。
    """
    state = load_state()
    task_desc = state.get('task', {}).get('description', '')
    return bool(task_desc.strip())
