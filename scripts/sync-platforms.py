#!/usr/bin/env python3
"""
sync-platforms.py —— 从 _shared/ 真源生成三平台独立可用的文件。

用法：
    python scripts/sync-platforms.py --format folders    # 生成文件夹包（默认）
    python scripts/sync-platforms.py --format plugins    # 生成插件包
    python scripts/sync-platforms.py --install /path/to/project --platform codebuddy  # 安装到项目（合并配置）

folders 模式：生成 CodeBuddy/、Codex/、ClaudeCode/ 三个目录
plugins 模式：生成 dist/ 下的各平台原生插件格式
install 模式：将 CEL 部署到用户项目目录，自动与已有配置合并（不覆盖其他系统的 hooks）
"""

import argparse
import json
import os
import re
import shutil
import zipfile
import yaml

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_DIR = os.path.join(ROOT_DIR, '_shared')

# CEL hooks 标识前缀（用于合并时识别旧版 CEL hooks）
CEL_HOOK_PREFIX = 'CEL '

# 各平台被 hook 拦截的文件修改工具名（方向 C：精确化 matcher）
PLATFORM_EDIT_MATCHERS = {
    'codebuddy': 'write_to_file|replace_in_file',
    # TODO: 确认 Claude Code 精确工具名后缩小范围
    'claude': 'edit_file|write|edit',
    # TODO: 确认 Codex 精确工具名后缩小范围
    'codex': 'edit|write',
}

# 各平台被 hook 拦截的命令执行工具名
PLATFORM_COMMAND_MATCHERS = {
    'codebuddy': 'execute_command',
    'claude': 'bash|shell|terminal',
    'codex': 'shell|run_command',
}


def ensure_dir(path):
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)


def clean_dir(path):
    """清空并重建目录。"""
    if os.path.exists(path):
        shutil.rmtree(path)
    ensure_dir(path)


def copy_file(src, dst):
    """复制文件。"""
    ensure_dir(os.path.dirname(dst))
    shutil.copy2(src, dst)


def copy_dir(src, dst):
    """递归复制目录。"""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_skill_dir(shared_skills_dir, target_skills_dir):
    """复制 skill 目录（SKILL.md + references + templates + checklists）。"""
    copy_dir(shared_skills_dir, target_skills_dir)


def read_agents_yaml():
    """读取 agents.yaml 元数据。"""
    yaml_path = os.path.join(SHARED_DIR, 'agents', 'agents.yaml')
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def read_agent_instruction(agent_name):
    """读取 agent 指令内容。"""
    md_path = os.path.join(SHARED_DIR, 'agents', 'instructions', f'{agent_name}.md')
    if os.path.exists(md_path):
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


def generate_codebuddy_agent(agent_name, agents_meta):
    """生成 CodeBuddy 格式的 agent（Markdown + YAML frontmatter）。"""
    instruction = read_agent_instruction(agent_name)
    meta = agents_meta.get('agents', {}).get(agent_name, {})

    # 从 YAML frontmatter 提取已有元数据（如果有）
    existing_meta = {}
    if instruction.startswith('---'):
        end = instruction.find('---', 3)
        if end > 0:
            frontmatter = instruction[3:end].strip()
            existing_meta = yaml.safe_load(frontmatter) or {}
            instruction = instruction[end + 3:].strip()

    # 合并元数据
    merged = {**existing_meta, **meta}
    if 'name' not in merged:
        merged['name'] = agent_name

    frontmatter_str = yaml.dump(merged, allow_unicode=True, default_flow_style=False).strip()

    return f"---\n{frontmatter_str}\n---\n\n{instruction}\n"


def generate_codex_agent(agent_name, agents_meta):
    """生成 Codex 格式的 agent（TOML）。"""
    instruction = read_agent_instruction(agent_name)
    meta = agents_meta.get('agents', {}).get(agent_name, {})

    # 从 YAML frontmatter 提取已有元数据
    existing_meta = {}
    if instruction.startswith('---'):
        end = instruction.find('---', 3)
        if end > 0:
            frontmatter = instruction[3:end].strip()
            existing_meta = yaml.safe_load(frontmatter) or {}
            instruction = instruction[end + 3:].strip()

    # 合并元数据
    merged = {**existing_meta, **meta}
    if 'name' not in merged:
        merged['name'] = agent_name

    # 生成 TOML
    lines = ['# 由 sync-platforms.py 自动生成，修改请改 _shared/ 下的真源']

    # 简单字段
    for key in ['name', 'description']:
        if key in merged:
            val = merged[key].replace('"', '\\"')
            lines.append(f'{key} = "{val}"')

    # instruction 字段（多行字符串）
    lines.append(f'instruction = """')
    lines.append(instruction)
    lines.append('"""')

    return '\n'.join(lines) + '\n'


def generate_claude_agent(agent_name, agents_meta):
    """生成 Claude Code 格式的 agent（与 CodeBuddy 相同：Markdown + YAML）。"""
    return generate_codebuddy_agent(agent_name, agents_meta)


# ============================================================
# CEL Hooks 常量定义（单一真源）
# ============================================================

HOOK_NAMES = [
    'cel-pre-edit-guard.py',
    'cel-dangerous-command-guard.py',
    'cel-post-edit-verify.py',
    'cel-oscillation-detector.py',
]

# 工具模板文件名映射：平台 → 模板文件名
UTILS_TEMPLATE_NAMES = {
    'codebuddy': 'cel_codebuddy_utils.py',
    'claude': 'cel_claude_utils.py',
    'codex': 'cel_codex_utils.py',
}

# 生成的工具模块文件名（统一，各平台 hook 脚本均 import cel_hook_utils）
UTILS_OUTPUT_NAME = 'cel_hook_utils.py'


def build_cel_hooks_codebuddy():
    """构建 CodeBuddy 平台的 CEL hooks 配置列表。"""
    edit_matcher = PLATFORM_EDIT_MATCHERS['codebuddy']
    cmd_matcher = PLATFORM_COMMAND_MATCHERS['codebuddy']
    return {
        "PreToolUse": [
            {
                "matcher": edit_matcher,
                "command": "python \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/cel-pre-edit-guard.py\"",
                "description": f"{CEL_HOOK_PREFIX}修改前守卫：检查最小修改原则"
            },
            {
                "matcher": cmd_matcher,
                "command": "python \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/cel-dangerous-command-guard.py\"",
                "description": f"{CEL_HOOK_PREFIX}危险命令拦截"
            }
        ],
        "PostToolUse": [
            {
                "matcher": edit_matcher,
                "command": "python \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/cel-post-edit-verify.py\"",
                "description": f"{CEL_HOOK_PREFIX}修改后验证提醒"
            },
            {
                "matcher": edit_matcher,
                "command": "python \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/cel-oscillation-detector.py\"",
                "description": f"{CEL_HOOK_PREFIX}震荡检测"
            }
        ]
    }


def build_cel_hooks_claude():
    """构建 Claude Code 平台的 CEL hooks 配置列表。"""
    edit_matcher = PLATFORM_EDIT_MATCHERS['claude']
    cmd_matcher = PLATFORM_COMMAND_MATCHERS['claude']
    return {
        "PreToolUse": [
            {
                "matcher": edit_matcher,
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/cel-pre-edit-guard.py\"",
                "description": f"{CEL_HOOK_PREFIX}修改前守卫：检查最小修改原则"
            },
            {
                "matcher": cmd_matcher,
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/cel-dangerous-command-guard.py\"",
                "description": f"{CEL_HOOK_PREFIX}危险命令拦截"
            }
        ],
        "PostToolUse": [
            {
                "matcher": edit_matcher,
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/cel-post-edit-verify.py\"",
                "description": f"{CEL_HOOK_PREFIX}修改后验证提醒"
            },
            {
                "matcher": edit_matcher,
                "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/cel-oscillation-detector.py\"",
                "description": f"{CEL_HOOK_PREFIX}震荡检测"
            }
        ]
    }


def build_cel_hooks_codex():
    """构建 Codex 平台的 CEL hooks 配置（TOML 格式行列表）。"""
    edit_matcher = PLATFORM_EDIT_MATCHERS['codex']
    cmd_matcher = PLATFORM_COMMAND_MATCHERS['codex']
    lines = []
    lines.append('# CEL Hook 配置')
    lines.append('[hooks.PreToolUse]')
    lines.append('[[hooks.PreToolUse.matchers]]')
    lines.append(f'pattern = "{edit_matcher}"')
    lines.append('command = "python .codex/hooks/cel-pre-edit-guard.py"')
    lines.append('description = "CEL 修改前守卫：检查最小修改原则"')
    lines.append('')
    lines.append('[[hooks.PreToolUse.matchers]]')
    lines.append(f'pattern = "{cmd_matcher}"')
    lines.append('command = "python .codex/hooks/cel-dangerous-command-guard.py"')
    lines.append('description = "CEL 危险命令拦截"')
    lines.append('')
    lines.append('[hooks.PostToolUse]')
    lines.append('[[hooks.PostToolUse.matchers]]')
    lines.append(f'pattern = "{edit_matcher}"')
    lines.append('command = "python .codex/hooks/cel-post-edit-verify.py"')
    lines.append('description = "CEL 修改后验证提醒"')
    lines.append('')
    lines.append('[[hooks.PostToolUse.matchers]]')
    lines.append(f'pattern = "{edit_matcher}"')
    lines.append('command = "python .codex/hooks/cel-oscillation-detector.py"')
    lines.append('description = "CEL 震荡检测"')
    return lines


# ============================================================
# 配置生成函数
# ============================================================

def _merge_json_hooks(settings, cel_hooks):
    """将 CEL hooks 合并到已有的 settings dict 中。

    策略：按 description 前缀识别旧版 CEL hooks，先移除再追加。
    保留其他系统已注册的 hooks 不受影响。
    """
    settings.setdefault('hooks', {})
    for event in ['PreToolUse', 'PostToolUse']:
        settings['hooks'].setdefault(event, [])
        # 移除旧版 CEL hooks
        settings['hooks'][event] = [
            h for h in settings['hooks'][event]
            if not h.get('description', '').startswith(CEL_HOOK_PREFIX)
        ]
        # 追加当前版本
        settings['hooks'][event].extend(cel_hooks.get(event, []))
    return settings


def generate_codebuddy_settings(codebuddy_dir, merge=False):
    """生成 CodeBuddy settings.json。

    Args:
        codebuddy_dir: .codebuddy 目录路径
        merge: 若为 True，读取已有 settings.json 并合并（不覆盖其他系统的 hooks）
    """
    settings_path = os.path.join(codebuddy_dir, 'settings.json')
    cel_hooks = build_cel_hooks_codebuddy()

    if merge and os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        settings = _merge_json_hooks(settings, cel_hooks)
    else:
        settings = {'hooks': cel_hooks}

    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def generate_claude_settings(claude_dir, merge=False):
    """生成 Claude Code settings.json。

    Args:
        claude_dir: .claude 目录路径
        merge: 若为 True，读取已有 settings.json 并合并（不覆盖其他系统的 hooks）
    """
    settings_path = os.path.join(claude_dir, 'settings.json')
    cel_hooks = build_cel_hooks_claude()

    if merge and os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        settings = _merge_json_hooks(settings, cel_hooks)
    else:
        settings = {'hooks': cel_hooks}

    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def generate_codex_config(codex_dir, agent_names, agents_meta, merge=False):
    """生成 Codex config.toml。

    Args:
        codex_dir: .codex 目录路径
        agent_names: agent 名称列表
        agents_meta: agents.yaml 元数据 dict
        merge: 若为 True，读取已有 config.toml 并合并
    """
    config_path = os.path.join(codex_dir, 'config.toml')
    cel_hook_lines = build_cel_hooks_codex()

    if merge and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        content = _merge_codex_toml(existing_content, agent_names, agents_meta, cel_hook_lines)
    else:
        # 全量生成
        lines = ['# 由 sync-platforms.py 自动生成，修改请改 _shared/ 下的真源', '']
        # agents 配置（使用 [agents.<name>] 命名子表格格式，Codex 不支持 [[agents]] 数组格式）
        lines.append('# CEL Agent 定义')
        for name in agent_names:
            desc = agents_meta.get('agents', {}).get(name, {}).get('description', name)
            lines.append(f'[agents.{name}]')
            lines.append(f'description = "{desc}"')
            lines.append(f'config_file = ".codex/agents/{name}.toml"')
            lines.append('')
        # CEL hooks 配置
        lines.extend(cel_hook_lines)
        content = '\n'.join(lines) + '\n'

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)


def _read_toml_block(lines, start):
    """读取从 start 开始的 TOML 块，返回 (block_lines, next_index)。

    块从 [[...]] 或 [...] 开始，到下一个 [[...]] 或 [...] 或文件结尾结束。
    """
    block = [lines[start]]
    i = start + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith('[[') or (stripped.startswith('[') and not stripped.startswith('[[')):
            break
        block.append(lines[i])
        i += 1
    return block, i


def _merge_codex_toml(existing_content, agent_names, agents_meta, cel_hook_lines):
    """合并 Codex config.toml，保留非 CEL 内容，替换 CEL 内容。

    策略（基于内容识别，不依赖标记注释）：
    1. 逐块解析 TOML
    2. 移除 CEL 相关的块：
       - [agents.cel-*] 命名子表格（Codex 格式）
       - [[agents]] 块中 name 以 "cel-" 开头的（旧版格式，兼容清理）
       - [[hooks.*.matchers]] 块中 command 含 "cel-" 的
       - [hooks.*] section header 如果后续无非 CEL 的 matchers
    3. 追加新的 CEL 内容
    """
    lines = existing_content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        # === 处理 [agents.cel-*] 命名子表格（Codex 正确格式） ===
        if stripped.startswith('[agents.cel-') and not stripped.startswith('[['):
            block, i = _read_toml_block(lines, i)
            # CEL agent，移除
            _remove_preceding_blank_and_comment(result)
            continue

        # === 处理 [[agents]] 块（旧版格式，兼容清理） ===
        if stripped == '[[agents]]':
            block, i = _read_toml_block(lines, i)
            is_cel = any('name = "cel-' in line or "name = 'cel-" in line for line in block)
            if is_cel:
                _remove_preceding_blank_and_comment(result)
                continue
            result.extend(block)
            continue

        # === 处理 [[hooks.*.matchers]] 块 ===
        if stripped.startswith('[[hooks.') and 'matchers]]' in stripped:
            block, i = _read_toml_block(lines, i)
            is_cel = any('cel-' in line or 'CEL' in line for line in block)
            if is_cel:
                _remove_preceding_blank_and_comment(result)
                continue
            result.extend(block)
            continue

        # === 处理 [hooks.*] section header ===
        if stripped.startswith('[hooks.') and not stripped.startswith('[['):
            pending_section_header_idx = len(result)
            result.append(lines[i])
            i += 1
            continue

        # === 跳过 CEL 相关注释 ===
        if stripped in ('# CEL Hook 配置', '# Hook 配置', '# CEL Agent 定义',
                        '# Agent 定义', '# CEL Agent 定义'):
            i += 1
            continue

        # === 其他行直接保留 ===
        result.append(lines[i])
        i += 1

    # 检查空的 [hooks.*] section（只有 header 没有后续 matchers）
    _remove_empty_hook_sections(result)

    # 后处理：移除残留的 CEL 相关注释行
    _cel_comment_set = {
        '# CEL Hook 配置', '# Hook 配置', '# CEL Agent 定义', '# Agent 定义',
    }
    result = [line for line in result if line.strip() not in _cel_comment_set]

    # 清理连续空行
    result = _collapse_blank_lines(result)

    # 追加 CEL agents（使用 [agents.<name>] 命名子表格格式）
    result.append('')
    result.append('# CEL Agent 定义')
    for name in agent_names:
        desc = agents_meta.get('agents', {}).get(name, {}).get('description', name)
        result.append(f'[agents.{name}]')
        result.append(f'description = "{desc}"')
        result.append(f'config_file = ".codex/agents/{name}.toml"')
        result.append('')

    # 追加 CEL hooks
    result.extend(cel_hook_lines)

    return '\n'.join(result) + '\n'


def _remove_preceding_blank_and_comment(lines):
    """移除列表末尾连续的空行和 CEL 相关注释行。"""
    while lines:
        stripped = lines[-1].strip()
        if stripped == '':
            lines.pop()
        elif stripped in ('# CEL Hook 配置', '# Hook 配置', '# CEL Agent 定义',
                          '# Agent 定义', '# CEL Agent 定义'):
            lines.pop()
        else:
            break


def _remove_empty_hook_sections(lines):
    """移除空的 [hooks.*] section header（后续没有 [[hooks.*.matchers]] 块）。"""
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith('[hooks.') and not stripped.startswith('[['):
            # 检查后续行：如果下一个非空行不是 [[hooks.*.matchers]]，则此 section 为空
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j >= len(lines) or not (lines[j].strip().startswith('[[hooks.') and 'matchers]]' in lines[j].strip()):
                # 空 section，移除 header 及后续空行
                lines.pop(i)
                while i < len(lines) and lines[i].strip() == '':
                    lines.pop(i)
                continue
        i += 1


def _collapse_blank_lines(lines):
    """将连续的空行压缩为最多一个。"""
    result = []
    prev_blank = False
    for line in lines:
        if line.strip() == '':
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        result.append(line)
    return result


def generate_initial_state(platform_dir):
    """生成初始状态文件。"""
    state = {
        "version": 1,
        "task": {
            "description": ""
        },
        "current_iteration": 0,
        "current_round_type": "evaluation",
        "iterations": [],
        "oscillation": {
            "detected": False,
            "pattern": "",
            "consecutive_no_improvement": 0
        }
    }

    state_path = os.path.join(platform_dir, 'cel-state.json')
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ============================================================
# 通用部署辅助函数
# ============================================================

def _deploy_hooks(shared_hooks_dir, target_hooks_dir, platform):
    """将 hook 脚本和平台工具模块部署到目标目录。"""
    ensure_dir(target_hooks_dir)
    for hook in HOOK_NAMES:
        copy_file(os.path.join(shared_hooks_dir, hook), os.path.join(target_hooks_dir, hook))
    # 复制平台特定的工具模块，输出名为统一的 cel_hook_utils.py
    template_name = UTILS_TEMPLATE_NAMES[platform]
    copy_file(
        os.path.join(shared_hooks_dir, 'templates', template_name),
        os.path.join(target_hooks_dir, UTILS_OUTPUT_NAME),
    )


def _deploy_agents(target_agents_dir, agent_names, agents_meta, platform):
    """部署 agent 文件到目标目录。"""
    ensure_dir(target_agents_dir)
    generator = {
        'codebuddy': generate_codebuddy_agent,
        'claude': generate_claude_agent,
        'codex': generate_codex_agent,
    }[platform]
    ext = '.toml' if platform == 'codex' else '.md'
    for name in agent_names:
        content = generator(name, agents_meta)
        with open(os.path.join(target_agents_dir, f'{name}{ext}'), 'w', encoding='utf-8') as f:
            f.write(content)


# ============================================================
# install 模式的清理辅助函数
# ============================================================

# 旧版工具模块文件名（已更名为 cel_hook_utils.py，需清理残留）
LEGACY_UTILS_FILENAME = 'hook_utils.py'


def _clean_cel_hooks_dir(target_hooks_dir):
    """清理目标 hooks 目录中的旧版 CEL 文件。

    清理范围：
    - cel-*.py（CEL hook 脚本）
    - cel_*.py（CEL 工具模块，如 cel_hook_utils.py）
    - hook_utils.py（旧版泛化命名的工具模块，升级残留）
    """
    if not os.path.exists(target_hooks_dir):
        return
    for f in os.listdir(target_hooks_dir):
        if f.startswith('cel-') and f.endswith('.py'):
            os.remove(os.path.join(target_hooks_dir, f))
        elif f.startswith('cel_') and f.endswith('.py'):
            os.remove(os.path.join(target_hooks_dir, f))
        elif f == LEGACY_UTILS_FILENAME:
            os.remove(os.path.join(target_hooks_dir, f))


def _clean_cel_agents_dir(target_agents_dir):
    """清理目标 agents 目录中的旧版 CEL agent 文件。

    清理范围：
    - cel-*.md / cel-*.toml（CEL agent 文件）
    """
    if not os.path.exists(target_agents_dir):
        return
    for f in os.listdir(target_agents_dir):
        if f.startswith('cel-') and (f.endswith('.md') or f.endswith('.toml')):
            os.remove(os.path.join(target_agents_dir, f))


def _clean_cel_skills_dir(target_skills_parent_dir):
    """清理目标 skills 父目录中的旧版 CEL skill 目录。

    清理范围：
    - convergent-engineering-loop/ 目录（CEL skill 目录）
    """
    skill_dir = os.path.join(target_skills_parent_dir, 'convergent-engineering-loop')
    if os.path.exists(skill_dir):
        shutil.rmtree(skill_dir)


# ============================================================
# folders 模式
# ============================================================

def generate_folders(output_dir):
    """生成文件夹包模式：CodeBuddy/、Codex/、ClaudeCode/。"""
    shared_skills = os.path.join(SHARED_DIR, 'skills', 'convergent-engineering-loop')
    shared_hooks = os.path.join(SHARED_DIR, 'hooks')
    agents_meta = read_agents_yaml()
    agent_names = list(agents_meta.get('agents', {}).keys())

    # 确保至少有默认的 agent 列表
    if not agent_names:
        instructions_dir = os.path.join(SHARED_DIR, 'agents', 'instructions')
        if os.path.exists(instructions_dir):
            agent_names = [
                os.path.splitext(f)[0]
                for f in os.listdir(instructions_dir)
                if f.endswith('.md')
            ]

    # ========== CodeBuddy ==========
    codebuddy_dir = os.path.join(output_dir, 'CodeBuddy', '.codebuddy')

    _deploy_hooks(shared_hooks, os.path.join(codebuddy_dir, 'hooks'), 'codebuddy')
    _deploy_agents(os.path.join(codebuddy_dir, 'agents'), agent_names, agents_meta, 'codebuddy')
    copy_skill_dir(shared_skills, os.path.join(codebuddy_dir, 'skills', 'convergent-engineering-loop'))
    generate_codebuddy_settings(codebuddy_dir)
    generate_initial_state(codebuddy_dir)

    # ========== Codex ==========
    codex_dir = os.path.join(output_dir, 'Codex', '.codex')
    agents_dir = os.path.join(output_dir, 'Codex', '.agents')

    _deploy_hooks(shared_hooks, os.path.join(codex_dir, 'hooks'), 'codex')
    _deploy_agents(os.path.join(codex_dir, 'agents'), agent_names, agents_meta, 'codex')
    copy_skill_dir(shared_skills, os.path.join(agents_dir, 'skills', 'convergent-engineering-loop'))
    generate_codex_config(codex_dir, agent_names, agents_meta)
    generate_initial_state(codex_dir)

    # ========== ClaudeCode ==========
    claude_dir = os.path.join(output_dir, 'ClaudeCode', '.claude')

    _deploy_hooks(shared_hooks, os.path.join(claude_dir, 'hooks'), 'claude')
    _deploy_agents(os.path.join(claude_dir, 'agents'), agent_names, agents_meta, 'claude')
    copy_skill_dir(shared_skills, os.path.join(claude_dir, 'skills', 'convergent-engineering-loop'))
    generate_claude_settings(claude_dir)
    generate_initial_state(claude_dir)


# ============================================================
# plugins 模式
# ============================================================

def generate_plugins(output_dir):
    """生成插件包模式。"""
    dist_dir = os.path.join(output_dir, 'dist')
    clean_dir(dist_dir)

    shared_skills = os.path.join(SHARED_DIR, 'skills', 'convergent-engineering-loop')
    shared_hooks = os.path.join(SHARED_DIR, 'hooks')
    agents_meta = read_agents_yaml()
    agent_names = list(agents_meta.get('agents', {}).keys())

    if not agent_names:
        instructions_dir = os.path.join(SHARED_DIR, 'agents', 'instructions')
        if os.path.exists(instructions_dir):
            agent_names = [
                os.path.splitext(f)[0]
                for f in os.listdir(instructions_dir)
                if f.endswith('.md')
            ]

    # ========== Claude Code 插件（一体化） ==========
    claude_plugin_dir = os.path.join(dist_dir, 'claude-cel-plugin')

    # .claude-plugin/plugin.json
    ensure_dir(os.path.join(claude_plugin_dir, '.claude-plugin'))
    plugin_json = {
        "name": "convergent-engineering-loop",
        "description": "收敛式工程迭代系统——Skill + Hook + Subagent 三层架构",
        "version": "1.0.0"
    }
    with open(os.path.join(claude_plugin_dir, '.claude-plugin', 'plugin.json'), 'w', encoding='utf-8') as f:
        json.dump(plugin_json, f, ensure_ascii=False, indent=2)

    # skills
    copy_skill_dir(shared_skills, os.path.join(claude_plugin_dir, 'skills', 'convergent-engineering-loop'))

    # hooks
    _deploy_hooks(shared_hooks, os.path.join(claude_plugin_dir, 'hooks'), 'claude')

    # agents
    _deploy_agents(os.path.join(claude_plugin_dir, 'agents'), agent_names, agents_meta, 'claude')

    # marketplace.json
    marketplace = {
        "name": "convergent-engineering-loop",
        "owner": "cel",
        "plugins": [
            {
                "name": "convergent-engineering-loop",
                "description": "收敛式工程迭代系统",
                "version": "1.0.0"
            }
        ]
    }
    with open(os.path.join(claude_plugin_dir, 'marketplace.json'), 'w', encoding='utf-8') as f:
        json.dump(marketplace, f, ensure_ascii=False, indent=2)

    # ========== CodeBuddy 插件（Skills ZIP + 辅助配置） ==========
    codebuddy_plugin_dir = os.path.join(dist_dir, 'codebuddy-cel-plugin')
    ensure_dir(codebuddy_plugin_dir)

    # Skills ZIP
    skill_zip_path = os.path.join(codebuddy_plugin_dir, 'convergent-engineering-loop.zip')
    with zipfile.ZipFile(skill_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(shared_skills):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, shared_skills)
                zf.write(file_path, arcname)

    # settings-hooks.json（用户需合并到 .codebuddy/settings.json）
    generate_codebuddy_settings(codebuddy_plugin_dir)
    # 重命名为 settings-hooks.json
    os.rename(
        os.path.join(codebuddy_plugin_dir, 'settings.json'),
        os.path.join(codebuddy_plugin_dir, 'settings-hooks.json'),
    )

    # agents
    _deploy_agents(os.path.join(codebuddy_plugin_dir, 'agents'), agent_names, agents_meta, 'codebuddy')

    # ========== Codex 插件（文件夹包，无原生插件格式） ==========
    codex_plugin_dir = os.path.join(dist_dir, 'codex-cel-plugin')

    # .codex/
    codex_dot_codex = os.path.join(codex_plugin_dir, '.codex')
    ensure_dir(codex_dot_codex)

    # hooks
    _deploy_hooks(shared_hooks, os.path.join(codex_dot_codex, 'hooks'), 'codex')

    # agents
    _deploy_agents(os.path.join(codex_dot_codex, 'agents'), agent_names, agents_meta, 'codex')

    # config.toml
    generate_codex_config(codex_dot_codex, agent_names, agents_meta)

    # .agents/skills
    copy_skill_dir(shared_skills, os.path.join(codex_plugin_dir, '.agents', 'skills', 'convergent-engineering-loop'))


# ============================================================
# install 模式（方向 A3：合并而非覆写）
# ============================================================

def install_to_project(project_dir, platform):
    """将 CEL 部署到用户项目目录，自动与已有配置合并。

    与 folders/plugins 模式的区别：
    - 配置文件（settings.json/config.toml）采用合并策略，保留其他系统的 hooks
    - cel-state.json 仅在不存在时创建，不覆盖运行时状态
    - agents/skills 文件直接覆盖（CEL 专属，不会冲突）
    """
    shared_skills = os.path.join(SHARED_DIR, 'skills', 'convergent-engineering-loop')
    shared_hooks = os.path.join(SHARED_DIR, 'hooks')
    agents_meta = read_agents_yaml()
    agent_names = list(agents_meta.get('agents', {}).keys())

    if not agent_names:
        instructions_dir = os.path.join(SHARED_DIR, 'agents', 'instructions')
        if os.path.exists(instructions_dir):
            agent_names = [
                os.path.splitext(f)[0]
                for f in os.listdir(instructions_dir)
                if f.endswith('.md')
            ]

    platforms = [platform] if platform != 'all' else ['codebuddy', 'claude', 'codex']

    for plat in platforms:
        if plat == 'codebuddy':
            plat_dir = os.path.join(project_dir, '.codebuddy')
            _install_codebuddy(plat_dir, shared_hooks, shared_skills, agent_names, agents_meta)
        elif plat == 'claude':
            plat_dir = os.path.join(project_dir, '.claude')
            _install_claude(plat_dir, shared_hooks, shared_skills, agent_names, agents_meta)
        elif plat == 'codex':
            codex_dir = os.path.join(project_dir, '.codex')
            agents_dir = os.path.join(project_dir, '.agents')
            _install_codex(codex_dir, agents_dir, shared_hooks, shared_skills, agent_names, agents_meta)
        else:
            print(f'未知平台：{plat}，跳过')

    print(f'CEL 已安装到 {project_dir}（平台：{", ".join(platforms)}）')
    print('配置文件已合并，其他系统的 hooks 不受影响。')


def _install_codebuddy(plat_dir, shared_hooks, shared_skills, agent_names, agents_meta):
    """安装 CodeBuddy 平台。"""
    ensure_dir(plat_dir)
    # 清理旧版 CEL 文件（处理升级场景）
    _clean_cel_hooks_dir(os.path.join(plat_dir, 'hooks'))
    _clean_cel_agents_dir(os.path.join(plat_dir, 'agents'))
    _clean_cel_skills_dir(os.path.join(plat_dir, 'skills'))
    # 部署新版
    _deploy_hooks(shared_hooks, os.path.join(plat_dir, 'hooks'), 'codebuddy')
    _deploy_agents(os.path.join(plat_dir, 'agents'), agent_names, agents_meta, 'codebuddy')
    copy_skill_dir(shared_skills, os.path.join(plat_dir, 'skills', 'convergent-engineering-loop'))
    # 合并配置（不覆盖其他系统的 hooks）
    generate_codebuddy_settings(plat_dir, merge=True)
    # 仅在不存在时创建状态文件（保留运行时状态）
    state_path = os.path.join(plat_dir, 'cel-state.json')
    if not os.path.exists(state_path):
        generate_initial_state(plat_dir)


def _install_claude(plat_dir, shared_hooks, shared_skills, agent_names, agents_meta):
    """安装 Claude Code 平台。"""
    ensure_dir(plat_dir)
    # 清理旧版 CEL 文件
    _clean_cel_hooks_dir(os.path.join(plat_dir, 'hooks'))
    _clean_cel_agents_dir(os.path.join(plat_dir, 'agents'))
    _clean_cel_skills_dir(os.path.join(plat_dir, 'skills'))
    # 部署新版
    _deploy_hooks(shared_hooks, os.path.join(plat_dir, 'hooks'), 'claude')
    _deploy_agents(os.path.join(plat_dir, 'agents'), agent_names, agents_meta, 'claude')
    copy_skill_dir(shared_skills, os.path.join(plat_dir, 'skills', 'convergent-engineering-loop'))
    generate_claude_settings(plat_dir, merge=True)
    state_path = os.path.join(plat_dir, 'cel-state.json')
    if not os.path.exists(state_path):
        generate_initial_state(plat_dir)


def _install_codex(codex_dir, agents_dir, shared_hooks, shared_skills, agent_names, agents_meta):
    """安装 Codex 平台。"""
    ensure_dir(codex_dir)
    # 清理旧版 CEL 文件
    _clean_cel_hooks_dir(os.path.join(codex_dir, 'hooks'))
    _clean_cel_agents_dir(os.path.join(codex_dir, 'agents'))
    _clean_cel_skills_dir(os.path.join(agents_dir, 'skills'))
    # 部署新版
    _deploy_hooks(shared_hooks, os.path.join(codex_dir, 'hooks'), 'codex')
    _deploy_agents(os.path.join(codex_dir, 'agents'), agent_names, agents_meta, 'codex')
    copy_skill_dir(shared_skills, os.path.join(agents_dir, 'skills', 'convergent-engineering-loop'))
    generate_codex_config(codex_dir, agent_names, agents_meta, merge=True)
    state_path = os.path.join(codex_dir, 'cel-state.json')
    if not os.path.exists(state_path):
        generate_initial_state(codex_dir)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='从 _shared/ 真源生成三平台独立可用的文件')
    parser.add_argument(
        '--format',
        choices=['folders', 'plugins'],
        default='folders',
        help='输出格式：folders（文件夹包）或 plugins（插件包）'
    )
    parser.add_argument(
        '--output',
        default=ROOT_DIR,
        help='输出目录（默认为项目根目录）'
    )
    parser.add_argument(
        '--install',
        metavar='PROJECT_DIR',
        help='将 CEL 安装到指定项目目录（合并配置，不覆盖其他系统 hooks）'
    )
    parser.add_argument(
        '--platform',
        choices=['codebuddy', 'claude', 'codex', 'all'],
        default='all',
        help='安装目标平台（仅 --install 模式，默认 all）'
    )

    args = parser.parse_args()

    if args.install:
        # install 模式
        project_dir = os.path.abspath(args.install)
        if not os.path.isdir(project_dir):
            print(f'错误：项目目录不存在：{project_dir}')
            return
        install_to_project(project_dir, args.platform)
    elif args.format == 'folders':
        # 清理旧输出
        for d in ['CodeBuddy', 'Codex', 'ClaudeCode']:
            clean_dir(os.path.join(args.output, d))
        generate_folders(args.output)
        print('已生成：')
        print(f'  {os.path.join(args.output, "CodeBuddy/")}')
        print(f'  {os.path.join(args.output, "Codex/")}')
        print(f'  {os.path.join(args.output, "ClaudeCode/")}')
    else:
        generate_plugins(args.output)
        print('已生成：')
        print(f'  {os.path.join(args.output, "dist", "claude-cel-plugin/")}')
        print(f'  {os.path.join(args.output, "dist", "codebuddy-cel-plugin/")}')
        print(f'  {os.path.join(args.output, "dist", "codex-cel-plugin/")}')


if __name__ == '__main__':
    main()
