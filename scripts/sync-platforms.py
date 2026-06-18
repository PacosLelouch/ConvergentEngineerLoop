#!/usr/bin/env python3
"""
sync-platforms.py —— 从 _shared/ 真源生成三平台独立可用的文件。

用法：
    python scripts/sync-platforms.py --format folders    # 生成文件夹包（默认）
    python scripts/sync-platforms.py --format plugins    # 生成插件包

folders 模式：生成 CodeBuddy/、Codex/、ClaudeCode/ 三个目录
plugins 模式：生成 dist/ 下的各平台原生插件格式
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

# 生成物头部标注
AUTO_GENERATED_HEADER = '# 由 sync-platforms.py 自动生成，修改请改 _shared/ 下的真源\n'


def ensure_dir(path):
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)


def clean_dir(path):
    """清空并重建目录。"""
    if os.path.exists(path):
        shutil.rmtree(path)
    ensure_dir(path)


def copy_file(src, dst, add_header=False):
    """复制文件，可选添加自动生成头部。"""
    ensure_dir(os.path.dirname(dst))
    if add_header and src.endswith('.py'):
        with open(src, 'r', encoding='utf-8') as f:
            content = f.read()
        # 如果文件已有自动生成头部，先移除
        if content.startswith('# 由 sync-platforms.py 自动生成'):
            content = content[len(AUTO_GENERATED_HEADER):]
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(AUTO_GENERATED_HEADER + content)
    else:
        shutil.copy2(src, dst)


def copy_dir(src, dst):
    """递归复制目录。"""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_skill_dir(shared_skills_dir, target_skills_dir):
    """复制 skill 目录（SKILL.md + references + templates + checklists）。"""
    copy_dir(shared_skills_dir, target_skills_dir)
    # 给 SKILL.md 添加头部标注
    skill_md = os.path.join(target_skills_dir, 'SKILL.md')
    if os.path.exists(skill_md):
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.startswith('<!-- 由 sync-platforms.py 自动生成'):
            with open(skill_md, 'w', encoding='utf-8') as f:
                f.write('<!-- 由 sync-platforms.py 自动生成，修改请改 _shared/skills/ 下的真源 -->\n' + content)


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
    lines = [AUTO_GENERATED_HEADER.rstrip()]

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

    # hooks
    codebuddy_hooks = os.path.join(codebuddy_dir, 'hooks')
    ensure_dir(codebuddy_hooks)
    for hook in ['pre-edit-guard.py', 'dangerous-command-guard.py', 'post-edit-verify.py', 'oscillation-detector.py']:
        copy_file(os.path.join(shared_hooks, hook), os.path.join(codebuddy_hooks, hook), add_header=True)
    copy_file(
        os.path.join(shared_hooks, 'templates', 'codebuddy_utils.py'),
        os.path.join(codebuddy_hooks, 'hook_utils.py'),
        add_header=True,
    )

    # agents
    codebuddy_agents = os.path.join(codebuddy_dir, 'agents')
    ensure_dir(codebuddy_agents)
    for name in agent_names:
        content = generate_codebuddy_agent(name, agents_meta)
        with open(os.path.join(codebuddy_agents, f'{name}.md'), 'w', encoding='utf-8') as f:
            f.write(content)

    # skills
    copy_skill_dir(shared_skills, os.path.join(codebuddy_dir, 'skills', 'convergent-engineering-loop'))

    # settings.json
    generate_codebuddy_settings(codebuddy_dir)

    # cel-state.json
    generate_initial_state(codebuddy_dir)

    # ========== Codex ==========
    codex_dir = os.path.join(output_dir, 'Codex', '.codex')
    agents_dir = os.path.join(output_dir, 'Codex', '.agents')

    # .codex/hooks
    codex_hooks = os.path.join(codex_dir, 'hooks')
    ensure_dir(codex_hooks)
    for hook in ['pre-edit-guard.py', 'dangerous-command-guard.py', 'post-edit-verify.py', 'oscillation-detector.py']:
        copy_file(os.path.join(shared_hooks, hook), os.path.join(codex_hooks, hook), add_header=True)
    copy_file(
        os.path.join(shared_hooks, 'templates', 'codex_utils.py'),
        os.path.join(codex_hooks, 'hook_utils.py'),
        add_header=True,
    )

    # .codex/agents
    codex_agents = os.path.join(codex_dir, 'agents')
    ensure_dir(codex_agents)
    for name in agent_names:
        content = generate_codex_agent(name, agents_meta)
        with open(os.path.join(codex_agents, f'{name}.toml'), 'w', encoding='utf-8') as f:
            f.write(content)

    # .agents/skills（Codex 的 skills 标准路径）
    copy_skill_dir(shared_skills, os.path.join(agents_dir, 'skills', 'convergent-engineering-loop'))

    # .codex/config.toml
    generate_codex_config(codex_dir, agent_names)

    # cel-state.json
    generate_initial_state(codex_dir)

    # ========== ClaudeCode ==========
    claude_dir = os.path.join(output_dir, 'ClaudeCode', '.claude')

    # hooks
    claude_hooks = os.path.join(claude_dir, 'hooks')
    ensure_dir(claude_hooks)
    for hook in ['pre-edit-guard.py', 'dangerous-command-guard.py', 'post-edit-verify.py', 'oscillation-detector.py']:
        copy_file(os.path.join(shared_hooks, hook), os.path.join(claude_hooks, hook), add_header=True)
    copy_file(
        os.path.join(shared_hooks, 'templates', 'claude_utils.py'),
        os.path.join(claude_hooks, 'hook_utils.py'),
        add_header=True,
    )

    # agents
    claude_agents = os.path.join(claude_dir, 'agents')
    ensure_dir(claude_agents)
    for name in agent_names:
        content = generate_claude_agent(name, agents_meta)
        with open(os.path.join(claude_agents, f'{name}.md'), 'w', encoding='utf-8') as f:
            f.write(content)

    # skills
    copy_skill_dir(shared_skills, os.path.join(claude_dir, 'skills', 'convergent-engineering-loop'))

    # settings.json
    generate_claude_settings(claude_dir)

    # cel-state.json
    generate_initial_state(claude_dir)


def generate_codebuddy_settings(codebuddy_dir):
    """生成 CodeBuddy settings.json。"""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "write_to_file|replace_in_file|edit_file|write|edit",
                    "command": "python3 \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/pre-edit-guard.py\"",
                    "description": "CEL 修改前守卫：检查最小修改原则"
                },
                {
                    "matcher": "execute_command|bash|shell|terminal|run_command",
                    "command": "python3 \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/dangerous-command-guard.py\"",
                    "description": "CEL 危险命令拦截"
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "write_to_file|replace_in_file|edit_file|write|edit",
                    "command": "python3 \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/post-edit-verify.py\"",
                    "description": "CEL 修改后验证提醒"
                },
                {
                    "matcher": "write_to_file|replace_in_file|edit_file|write|edit",
                    "command": "python3 \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/oscillation-detector.py\"",
                    "description": "CEL 震荡检测"
                }
            ]
        }
    }

    settings_path = os.path.join(codebuddy_dir, 'settings.json')
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def generate_codex_config(codex_dir, agent_names):
    """生成 Codex config.toml。"""
    lines = [AUTO_GENERATED_HEADER.rstrip(), '']

    # agents 配置
    lines.append('# Agent 定义')
    for name in agent_names:
        lines.append(f'[[agents]]')
        lines.append(f'name = "{name}"')
        lines.append(f'instruction_file = ".codex/agents/{name}.toml"')
        lines.append('')

    # hooks 配置
    lines.append('# Hook 配置')
    lines.append('')
    lines.append('[hooks.PreToolUse]')
    lines.append('[[hooks.PreToolUse.matchers]]')
    lines.append('pattern = "write_to_file|replace_in_file|edit_file|write|edit"')
    lines.append('command = "python3 .codex/hooks/pre-edit-guard.py"')
    lines.append('commandWindows = "python .codex/hooks/pre-edit-guard.py"')
    lines.append('')
    lines.append('[[hooks.PreToolUse.matchers]]')
    lines.append('pattern = "execute_command|bash|shell|terminal|run_command"')
    lines.append('command = "python3 .codex/hooks/dangerous-command-guard.py"')
    lines.append('commandWindows = "python .codex/hooks/dangerous-command-guard.py"')
    lines.append('')
    lines.append('[hooks.PostToolUse]')
    lines.append('[[hooks.PostToolUse.matchers]]')
    lines.append('pattern = "write_to_file|replace_in_file|edit_file|write|edit"')
    lines.append('command = "python3 .codex/hooks/post-edit-verify.py"')
    lines.append('commandWindows = "python .codex/hooks/post-edit-verify.py"')
    lines.append('')
    lines.append('[[hooks.PostToolUse.matchers]]')
    lines.append('pattern = "write_to_file|replace_in_file|edit_file|write|edit"')
    lines.append('command = "python3 .codex/hooks/oscillation-detector.py"')
    lines.append('commandWindows = "python .codex/hooks/oscillation-detector.py"')

    config_path = os.path.join(codex_dir, 'config.toml')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def generate_claude_settings(claude_dir):
    """生成 Claude Code settings.json。"""
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "write_to_file|replace_in_file|edit_file|write|edit",
                    "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/pre-edit-guard.py\"",
                    "description": "CEL 修改前守卫：检查最小修改原则"
                },
                {
                    "matcher": "execute_command|bash|shell|terminal|run_command",
                    "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/dangerous-command-guard.py\"",
                    "description": "CEL 危险命令拦截"
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "write_to_file|replace_in_file|edit_file|write|edit",
                    "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/post-edit-verify.py\"",
                    "description": "CEL 修改后验证提醒"
                },
                {
                    "matcher": "write_to_file|replace_in_file|edit_file|write|edit",
                    "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/oscillation-detector.py\"",
                    "description": "CEL 震荡检测"
                }
            ]
        }
    }

    settings_path = os.path.join(claude_dir, 'settings.json')
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


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
    claude_hooks = os.path.join(claude_plugin_dir, 'hooks')
    ensure_dir(claude_hooks)
    for hook in ['pre-edit-guard.py', 'dangerous-command-guard.py', 'post-edit-verify.py', 'oscillation-detector.py']:
        copy_file(os.path.join(shared_hooks, hook), os.path.join(claude_hooks, hook), add_header=True)
    copy_file(
        os.path.join(shared_hooks, 'templates', 'claude_utils.py'),
        os.path.join(claude_hooks, 'hook_utils.py'),
        add_header=True,
    )

    # agents
    claude_agents = os.path.join(claude_plugin_dir, 'agents')
    ensure_dir(claude_agents)
    for name in agent_names:
        content = generate_claude_agent(name, agents_meta)
        with open(os.path.join(claude_agents, f'{name}.md'), 'w', encoding='utf-8') as f:
            f.write(content)

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
    codebuddy_agents = os.path.join(codebuddy_plugin_dir, 'agents')
    ensure_dir(codebuddy_agents)
    for name in agent_names:
        content = generate_codebuddy_agent(name, agents_meta)
        with open(os.path.join(codebuddy_agents, f'{name}.md'), 'w', encoding='utf-8') as f:
            f.write(content)

    # ========== Codex 插件（文件夹包，无原生插件格式） ==========
    codex_plugin_dir = os.path.join(dist_dir, 'codex-cel-plugin')

    # .codex/
    codex_dot_codex = os.path.join(codex_plugin_dir, '.codex')
    ensure_dir(codex_dot_codex)

    # hooks
    codex_hooks = os.path.join(codex_dot_codex, 'hooks')
    ensure_dir(codex_hooks)
    for hook in ['pre-edit-guard.py', 'dangerous-command-guard.py', 'post-edit-verify.py', 'oscillation-detector.py']:
        copy_file(os.path.join(shared_hooks, hook), os.path.join(codex_hooks, hook), add_header=True)
    copy_file(
        os.path.join(shared_hooks, 'templates', 'codex_utils.py'),
        os.path.join(codex_hooks, 'hook_utils.py'),
        add_header=True,
    )

    # agents
    codex_agents = os.path.join(codex_dot_codex, 'agents')
    ensure_dir(codex_agents)
    for name in agent_names:
        content = generate_codex_agent(name, agents_meta)
        with open(os.path.join(codex_agents, f'{name}.toml'), 'w', encoding='utf-8') as f:
            f.write(content)

    # config.toml
    generate_codex_config(codex_dot_codex, agent_names)

    # .agents/skills
    copy_skill_dir(shared_skills, os.path.join(codex_plugin_dir, '.agents', 'skills', 'convergent-engineering-loop'))


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

    args = parser.parse_args()

    print(f'从 _shared/ 真源生成 {args.format} 格式的平台文件...')

    if args.format == 'folders':
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
