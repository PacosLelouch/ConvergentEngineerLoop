"""CodeBuddy 平台的 CEL Hook 工具模块。

提供：
- 输出格式适配（format_deny/allow/ask/additional_context）
- 状态文件读写（load_state/save_state）
- CEL 激活检查（is_cel_active）
- 平台特定工具名集合（EDIT_TOOLS/COMMAND_TOOLS）
"""

import json
import os
import sys


# 本平台被 hook 拦截的文件修改工具名
EDIT_TOOLS = {'write_to_file', 'replace_in_file'}

# 本平台被 hook 拦截的命令执行工具名
COMMAND_TOOLS = {'execute_command'}


def format_deny(reason):
    """生成 CodeBuddy deny 响应。"""
    return {"permissionDecision": "deny", "reason": reason}


def format_allow(reason=""):
    """生成 CodeBuddy allow 响应。"""
    result = {"permissionDecision": "allow"}
    if reason:
        result["reason"] = reason
    return result


def format_ask(reason):
    """生成 CodeBuddy ask 响应（请求用户确认）。"""
    return {"permissionDecision": "ask", "reason": reason}


def format_additional_context(context):
    """生成 CodeBuddy additionalContext 响应（注入上下文但不阻止）。"""
    return {"additionalContext": context}


# 状态文件路径
STATE_FILE = os.path.join(
    os.environ.get('CODEBUDDY_PROJECT_DIR', '.'), '.codebuddy', 'cel-state.json'
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
