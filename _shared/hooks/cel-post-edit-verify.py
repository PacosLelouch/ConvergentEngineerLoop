"""
修改后验证提醒 Hook。

在 Agent 完成文件修改后，通过 additionalContext/systemMessage 注入验证提醒：
1. 提醒执行相关测试
2. 提醒检查构建状态
3. 提醒验证修改效果

此 Hook 不阻止操作，仅注入上下文提醒 Agent 进行验证。
"""

import json
import os
import re
import sys

from cel_hook_utils import format_additional_context, format_allow, output, is_cel_active, EDIT_TOOLS


# 文件类型对应的验证建议
FILE_TYPE_VALIDATIONS = {
    r'\.py$': [
        '运行相关测试：python -m pytest <相关测试文件>',
        '运行类型检查：python -m mypy <修改的模块>',
        '运行 Lint：python -m ruff check <修改的文件>',
    ],
    r'\.(ts|tsx)$': [
        '运行相关测试：npx jest <相关测试文件>',
        '运行类型检查：npx tsc --noEmit',
        '运行 Lint：npx eslint <修改的文件>',
    ],
    r'\.(js|jsx)$': [
        '运行相关测试：npx jest <相关测试文件>',
        '运行 Lint：npx eslint <修改的文件>',
    ],
    r'\.(go)$': [
        '运行相关测试：go test ./<修改的包>/...',
        '运行构建：go build ./...',
        '运行 Lint：golangci-lint run <修改的目录>',
    ],
    r'\.(rs)$': [
        '运行相关测试：cargo test',
        '运行构建：cargo build',
        '运行 Lint：cargo clippy',
    ],
    r'\.(java)$': [
        '运行相关测试：mvn test -pl <模块>',
        '运行构建：mvn compile',
    ],
    r'\.(md|mdx)$': [
        '检查文档中的链接和示例是否有效',
        '确认文档与代码实现一致',
    ],
    r'\.(yaml|yml)$': [
        '验证 YAML 语法：python -c "import yaml; yaml.safe_load(open(\'<文件>\'))"',
        '如果是 CI 配置，检查工作流语法',
    ],
    r'\.(toml)$': [
        '验证 TOML 语法：python -c "import tomllib; tomllib.load(open(\'<文件>\', \'rb\'))"',
    ],
    r'Dockerfile$': [
        '验证 Docker 构建：docker build --check .',
        '检查镜像大小和安全扫描',
    ],
}

# 通用验证提醒
GENERAL_REMINDERS = [
    '请使用外部验证确认修改效果，不要仅依赖模型判断',
    '比较修改前后的误差度量，确认误差下降或不变',
]


def get_validation_suggestions(filepath):
    """根据文件类型返回验证建议。"""
    suggestions = []

    if filepath:
        basename = os.path.basename(filepath)
        for pattern, validations in FILE_TYPE_VALIDATIONS.items():
            if re.search(pattern, basename, re.IGNORECASE):
                suggestions.extend(validations)
                break

    if not suggestions:
        suggestions.append('运行相关测试验证修改效果')

    suggestions.extend(GENERAL_REMINDERS)
    return suggestions


def main():
    """主入口：读取 stdin 中的 Hook 输入，注入验证提醒。"""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        output(format_allow())

    # CEL 未激活时直接放行，不干扰其他系统
    if not is_cel_active():
        output(format_allow())

    # 从 Hook 输入中提取工具调用信息
    tool_name = data.get('tool_name', data.get('tool', ''))
    tool_input = data.get('tool_input', data.get('input', {}))

    # 只在文件修改类工具后触发（使用平台特定的工具名集合）
    if tool_name.lower() not in EDIT_TOOLS:
        output(format_allow())

    filepath = tool_input.get('filePath', tool_input.get('path', tool_input.get('file', '')))

    # 生成验证提醒
    suggestions = get_validation_suggestions(filepath)
    context = "[CEL 验证提醒]\n" + "\n".join(f"- {s}" for s in suggestions)

    output(format_additional_context(context))


if __name__ == '__main__':
    main()
