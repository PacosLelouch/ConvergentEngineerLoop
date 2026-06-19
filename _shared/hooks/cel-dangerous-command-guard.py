"""
危险命令拦截 Hook。

在 Agent 执行 shell 命令前检查：
1. 是否包含破坏性命令（rm -rf、force push、drop database 等）
2. 是否包含不可逆操作
3. 是否包含安全风险操作

通过 from cel_hook_utils import ... 调用平台特定的输出格式。
"""

import json
import re
import sys

from cel_hook_utils import format_deny, format_allow, format_ask, output, is_cel_active, COMMAND_TOOLS


# 完全禁止的命令模式
DENIED_PATTERNS = [
    (r'\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|-rf\s+|-fr\s+)(/(var|etc|usr|opt|tmp|home)|/)',
     '禁止递归强制删除系统关键目录'),
    (r'\bgit\s+push\s+.*--force\b', '禁止 force push，这会重写远程历史'),
    (r'\bgit\s+push\s+.*-f\b', '禁止 force push，这会重写远程历史'),
    (r'\bgit\s+reset\s+--hard\b', '禁止 hard reset，这会丢失未提交的更改'),
    (r'\bgit\s+clean\s+(-[a-zA-Z]*f[a-zA-Z]*|-xf)', '禁止 force clean，这会丢失未跟踪文件'),
    (r'\bdrop\s+database\b', '禁止删除数据库'),
    (r'\btruncate\s+table\b', '禁止清空表（生产环境风险）'),
    (r'\bchmod\s+777\b', '禁止设置 777 权限，存在安全风险'),
    (r'\bcurl\s+.*\|\s*sh\b', '禁止从网络管道执行脚本'),
    (r'\bwget\s+.*\|\s*sh\b', '禁止从网络管道执行脚本'),
    (r'\bdd\s+if=.*of=/dev/', '禁止直接写入设备文件'),
    (r'\bmkfs\b', '禁止格式化文件系统'),
    (r'>\s*/dev/sd', '禁止直接写入磁盘设备'),
    (r'\bsudo\s+rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|-rf\s+)', '禁止 sudo 删除文件'),
    (r'\bshutdown\b', '禁止关机命令'),
    (r'\breboot\b', '禁止重启命令'),
    (r'\biptables\s+-F\b', '禁止清空防火墙规则'),
]

# 需要用户确认的命令模式
ASK_PATTERNS = [
    (r'\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|-r\s+)', '递归或强制删除文件，请确认目标正确'),
    (r'\bgit\s+push\b', '推送到远程仓库，请确认分支和内容'),
    (r'\bgit\s+reset\b', '重置 Git 状态，请确认不会丢失重要更改'),
    (r'\bgit\s+checkout\s+\.', '丢弃所有工作区修改'),
    (r'\bsudo\b', '使用 sudo 权限执行命令，请确认必要性'),
    (r'\bdocker\s+(rm|rmi)\b', '删除 Docker 容器或镜像'),
    (r'\bnpm\s+publish\b', '发布 npm 包'),
    (r'\bpip\s+install\b.*--user\b', '全局安装 Python 包'),
    (r'\bmigrate\b.*--no-input\b', '跳过确认的数据库迁移'),
]


def check_command(command_str):
    """检查命令字符串是否包含危险操作。

    返回：
        (decision, reason) - decision 为 'deny'、'ask' 或 'allow'
    """
    if not command_str:
        return 'allow', ''

    # 检查禁止模式
    for pattern, reason in DENIED_PATTERNS:
        if re.search(pattern, command_str, re.IGNORECASE):
            return 'deny', f"危险命令拦截：{reason}。命令：{command_str[:100]}"

    # 检查需要确认的模式
    for pattern, reason in ASK_PATTERNS:
        if re.search(pattern, command_str, re.IGNORECASE):
            return 'ask', f"需要确认：{reason}。命令：{command_str[:100]}"

    return 'allow', ''


def main():
    """主入口：读取 stdin 中的 Hook 输入，执行检查，输出结果。"""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        output(format_allow())

    # CEL 未激活时直接放行，不干扰其他系统
    if not is_cel_active():
        output(format_allow())

    # 从 Hook 输入中提取命令
    tool_name = data.get('tool_name', data.get('tool', ''))
    tool_input = data.get('tool_input', data.get('input', {}))

    # 只拦截命令执行类工具（使用平台特定的工具名集合）
    if tool_name.lower() not in COMMAND_TOOLS:
        output(format_allow())

    command_str = tool_input.get('command', tool_input.get('cmd', ''))

    decision, reason = check_command(command_str)

    if decision == 'deny':
        output(format_deny(reason))
    elif decision == 'ask':
        output(format_ask(reason))
    else:
        output(format_allow())


if __name__ == '__main__':
    main()
