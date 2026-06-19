"""
修改前守卫 Hook。

在 Agent 执行文件修改操作前检查：
1. 是否违反最小修改原则（修改范围过大）
2. 是否修改了不应修改的文件（测试断言、公共接口等）
3. 是否有明确的验证计划

通过 from cel_hook_utils import ... 调用平台特定的输出格式。
"""

import json
import os
import re
import sys

# Python 运行时自动将脚本所在目录加入 sys.path
# 因此 from cel_hook_utils import ... 可以找到同目录下的 cel_hook_utils.py
from cel_hook_utils import (
    format_deny, format_allow, format_ask, format_additional_context,
    output, is_cel_active, EDIT_TOOLS,
)


# 不应被削弱的测试文件模式
TEST_FILE_PATTERNS = [
    r'test[_\-]',
    r'[_\-]test\.',
    r'spec[_\-]',
    r'__tests__',
    r'\.test\.',
    r'\.spec\.',
]

# 危险修改模式（在测试文件中）
DANGEROUS_TEST_PATTERNS = [
    r'skip\(',
    r'xit\(',
    r'xdescribe\(',
    r'\.todo\(',
    r'assert\.True\b',
    r'expect\(.*\)\.toBeTrue\b',
]

# 不应随意修改的配置文件
PROTECTED_FILE_PATTERNS = [
    r'^\.git',
    r'^\.env$',
    r'^package-lock\.json$',
    r'^yarn\.lock$',
    r'^poetry\.lock$',
]

# 一次修改的文件数上限
MAX_FILES_PER_EDIT = 5

# 一次修改的总行数上限
MAX_LINES_PER_EDIT = 200


def is_test_file(filepath):
    """判断文件是否为测试文件。"""
    basename = os.path.basename(filepath)
    return any(re.search(p, basename) for p in TEST_FILE_PATTERNS)


def is_protected_file(filepath):
    """判断文件是否为受保护文件。"""
    basename = os.path.basename(filepath)
    return any(re.search(p, basename) for p in PROTECTED_FILE_PATTERNS)


def check_test_weakening(filepath, content):
    """检查测试文件中是否有削弱断言的修改。"""
    if not is_test_file(filepath):
        return None

    for pattern in DANGEROUS_TEST_PATTERNS:
        if re.search(pattern, content):
            return f"检测到测试文件 {filepath} 中可能存在削弱断言的修改（匹配模式：{pattern}）"

    return None


def check_edit_scale(file_count, total_lines):
    """检查修改规模是否过大。"""
    if file_count > MAX_FILES_PER_EDIT:
        return (
            f"修改范围过大：涉及 {file_count} 个文件"
            f"（上限 {MAX_FILES_PER_EDIT}）。"
            f"请缩小修改范围，每轮只做最小修改。"
        )

    if total_lines > MAX_LINES_PER_EDIT:
        return (
            f"修改行数过多：共 {total_lines} 行"
            f"（上限 {MAX_LINES_PER_EDIT}）。"
            f"请缩小修改范围，每轮只做最小修改。"
        )

    return None


def main():
    """主入口：读取 stdin 中的 Hook 输入，执行检查，输出结果。"""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # 无法解析输入，放行
        output(format_allow())

    # CEL 未激活时直接放行，不干扰其他系统
    if not is_cel_active():
        output(format_allow())

    # 从 Hook 输入中提取工具调用信息
    tool_name = data.get('tool_name', data.get('tool', ''))
    tool_input = data.get('tool_input', data.get('input', {}))

    # 只拦截文件修改类工具（使用平台特定的工具名集合）
    # Codex 工具名区分大小写（Edit/Write/apply_patch），用大小写不敏感匹配做兼容
    if tool_name not in EDIT_TOOLS and tool_name.lower() not in {t.lower() for t in EDIT_TOOLS}:
        output(format_allow())

    filepath = tool_input.get('filePath', tool_input.get('path', tool_input.get('file', '')))
    content = tool_input.get('new_str', tool_input.get('content', ''))
    old_content = tool_input.get('old_str', tool_input.get('old_content', ''))

    # 检查受保护文件
    if filepath and is_protected_file(filepath):
        output(format_deny(
            f"禁止修改受保护文件：{filepath}。"
            f"此类文件不应由 Agent 自动修改。"
        ))

    # 检查测试削弱
    if filepath and content:
        weakening = check_test_weakening(filepath, content)
        if weakening:
            output(format_deny(weakening))

    # 检查修改规模
    new_lines = content.count('\n') + 1 if content else 0
    scale_issue = check_edit_scale(1, new_lines)
    if scale_issue:
        output(format_ask(scale_issue))

    # 所有检查通过，放行并提醒验证
    output(format_allow())


if __name__ == '__main__':
    main()
