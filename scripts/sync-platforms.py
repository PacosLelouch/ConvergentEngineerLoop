#!/usr/bin/env python3
"""
sync-platforms.py —— 从 _shared/ 真源生成三平台独立可用的文件。

用法：
    python scripts/sync-platforms.py --format folders    # 生成文件夹包（默认）
    python scripts/sync-platforms.py --format plugins    # 生成插件包
    python scripts/sync-platforms.py --install /path/to/project --platform codebuddy  # 安装到项目（清理旧版配置）

folders 模式：生成 CodeBuddy/、Codex/、ClaudeCode/ 三个目录
plugins 模式：生成 dist/ 下的各平台原生插件格式
install 模式：将 CEL 部署到用户项目目录，自动清理旧版 hooks 和配置
"""

import argparse
import json
import os
import shutil
import zipfile
import yaml

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_DIR = os.path.join(ROOT_DIR, '_shared')

# CEL hooks 标识前缀（用于合并时识别旧版 CEL hooks）
CEL_HOOK_PREFIX = 'CEL '




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
    """生成 Codex 格式的 agent（TOML）。

    Codex 自动扫描 .codex/agents/*.toml，无需在 config.toml 注册。
    必需字段：name、description、developer_instructions。
    """
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

    # developer_instructions 字段（多行字符串，Codex subagent 必需）
    lines.append(f'developer_instructions = """')
    lines.append(instruction)
    lines.append('"""')

    return '\n'.join(lines) + '\n'


def generate_claude_agent(agent_name, agents_meta):
    """生成 Claude Code 格式的 agent（与 CodeBuddy 相同：Markdown + YAML）。"""
    return generate_codebuddy_agent(agent_name, agents_meta)




















# ============================================================
# 通用部署辅助函数
# ============================================================




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


def _clean_legacy_state(platform_dir):
    """清理旧版 cel-state.json（升级迁移）。

    无状态化重构后，cel-state.json 不再使用。安装时删除旧版文件。
    """
    state_path = os.path.join(platform_dir, 'cel-state.json')
    if os.path.exists(state_path):
        os.remove(state_path)


def _clean_codex_config_toml(config_path):
    """清理 Codex config.toml 中的 CEL 残留。

    清理范围：
    - [agents.cel-*] 命名子表格（旧版注册格式）
    - [[agents]] 块中 name 以 "cel-" 开头的（更旧版格式）
    - [[hooks.*]] 内联 hooks 块
    - CEL 相关注释行
    """
    if not os.path.exists(config_path):
        return
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    result = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # 跳过 [agents.cel-*] 命名子表格
        if stripped.startswith('[agents.cel-') and not stripped.startswith('[['):
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('[') or s.startswith('[['):
                    break
                i += 1
            _remove_trailing_blank(result)
            continue

        # 跳过 [[agents]] 块中 name 以 "cel-" 开头的
        if stripped == '[[agents]]':
            block_start = i
            block = [lines[i]]
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('[') or s.startswith('[['):
                    break
                block.append(lines[i])
                i += 1
            is_cel = any('name = "cel-' in line or "name = 'cel-" in line for line in block)
            if is_cel:
                _remove_trailing_blank(result)
                continue
            result.extend(block)
            continue

        # 跳过 [[hooks.*]] 块
        if stripped.startswith('[[hooks.'):
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith('[') or s.startswith('[['):
                    break
                i += 1
            _remove_trailing_blank(result)
            continue

        # 跳过 CEL 相关注释
        if stripped in ('# CEL Hook 配置', '# Hook 配置', '# CEL Agent 定义',
                        '# Agent 定义'):
            i += 1
            continue

        result.append(lines[i])
        i += 1

    # 清理连续空行
    cleaned = []
    prev_blank = False
    for line in result:
        if line.strip() == '':
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        cleaned.append(line)

    # 如果清理后内容为空或只有注释，写入最小文件
    output = '\n'.join(cleaned).strip()
    if not output or all(line.strip().startswith('#') or line.strip() == '' for line in output.split('\n')):
        output = '# 由 sync-platforms.py 自动生成，修改请改 _shared/ 下的真源'
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(output + '\n')


def _remove_trailing_blank(lines):
    """移除列表末尾连续的空行。"""
    while lines and lines[-1].strip() == '':
        lines.pop()


# ============================================================
# folders 模式
# ============================================================

def generate_folders(output_dir):
    """生成文件夹包模式：CodeBuddy/、Codex/、ClaudeCode/。"""
    shared_skills = os.path.join(SHARED_DIR, 'skills', 'convergent-engineering-loop')
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

    _deploy_agents(os.path.join(codebuddy_dir, 'agents'), agent_names, agents_meta, 'codebuddy')
    copy_skill_dir(shared_skills, os.path.join(codebuddy_dir, 'skills', 'convergent-engineering-loop'))

    # ========== Codex ==========
    codex_dir = os.path.join(output_dir, 'Codex', '.codex')
    agents_dir = os.path.join(output_dir, 'Codex', '.agents')

    _deploy_agents(os.path.join(codex_dir, 'agents'), agent_names, agents_meta, 'codex')
    copy_skill_dir(shared_skills, os.path.join(agents_dir, 'skills', 'convergent-engineering-loop'))

    # ========== ClaudeCode ==========
    claude_dir = os.path.join(output_dir, 'ClaudeCode', '.claude')

    _deploy_agents(os.path.join(claude_dir, 'agents'), agent_names, agents_meta, 'claude')
    copy_skill_dir(shared_skills, os.path.join(claude_dir, 'skills', 'convergent-engineering-loop'))


# ============================================================
# plugins 模式
# ============================================================

def generate_plugins(output_dir):
    """生成插件包模式。"""
    dist_dir = os.path.join(output_dir, 'dist')
    clean_dir(dist_dir)

    shared_skills = os.path.join(SHARED_DIR, 'skills', 'convergent-engineering-loop')
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
        "description": "收敛式工程迭代系统——Skill + Subagent 两层架构",
        "version": "1.0.0"
    }
    with open(os.path.join(claude_plugin_dir, '.claude-plugin', 'plugin.json'), 'w', encoding='utf-8') as f:
        json.dump(plugin_json, f, ensure_ascii=False, indent=2)

    # skills
    copy_skill_dir(shared_skills, os.path.join(claude_plugin_dir, 'skills', 'convergent-engineering-loop'))

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

    # agents
    _deploy_agents(os.path.join(codebuddy_plugin_dir, 'agents'), agent_names, agents_meta, 'codebuddy')

    # ========== Codex 插件（文件夹包，无原生插件格式） ==========
    codex_plugin_dir = os.path.join(dist_dir, 'codex-cel-plugin')

    # .codex/
    codex_dot_codex = os.path.join(codex_plugin_dir, '.codex')
    ensure_dir(codex_dot_codex)

    # agents
    _deploy_agents(os.path.join(codex_dot_codex, 'agents'), agent_names, agents_meta, 'codex')

    # .agents/skills
    copy_skill_dir(shared_skills, os.path.join(codex_plugin_dir, '.agents', 'skills', 'convergent-engineering-loop'))


# ============================================================
# install 模式（方向 A3：合并而非覆写）
# ============================================================

def install_to_project(project_dir, platform):
    """将 CEL 部署到用户项目目录，自动清理旧版配置。

    与 folders/plugins 模式的区别：
    - 清理旧版 CEL hooks 和 cel-state.json（无状态化重构后不再使用）
    - 清理旧版 settings.json 中的 CEL hooks 注册
    - agents/skills 文件直接覆盖（CEL 专属，不会冲突）
    """
    shared_skills = os.path.join(SHARED_DIR, 'skills', 'convergent-engineering-loop')
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
            _install_codebuddy(plat_dir, shared_skills, agent_names, agents_meta)
        elif plat == 'claude':
            plat_dir = os.path.join(project_dir, '.claude')
            _install_claude(plat_dir, shared_skills, agent_names, agents_meta)
        elif plat == 'codex':
            codex_dir = os.path.join(project_dir, '.codex')
            agents_dir = os.path.join(project_dir, '.agents')
            _install_codex(codex_dir, agents_dir, shared_skills, agent_names, agents_meta)
        else:
            print(f'未知平台：{plat}，跳过')

    print(f'CEL 已安装到 {project_dir}（平台：{", ".join(platforms)}）')


def _clean_cel_hooks_from_settings(settings_path):
    """从 settings.json 或 hooks.json 中移除 CEL hooks 注册。

    识别规则（任一匹配即移除）：
    - CodeBuddy/Claude 格式：顶层 description 前缀为 "CEL "
    - Codex 格式：嵌套 hooks[].statusMessage 前缀为 "CEL "
    """
    if not os.path.exists(settings_path):
        return
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
    if 'hooks' not in settings:
        return
    changed = False
    for event in settings['hooks']:
        original = settings['hooks'][event]
        if not isinstance(original, list):
            continue
        # 同时匹配 CodeBuddy/Claude（description）和 Codex（statusMessage）格式
        filtered = [
            group for group in original
            if not group.get('description', '').startswith(CEL_HOOK_PREFIX)
            and not any(
                h.get('statusMessage', '').startswith(CEL_HOOK_PREFIX)
                for h in (group.get('hooks', []) if isinstance(group, dict) else [])
            )
        ]
        if len(filtered) != len(original):
            settings['hooks'][event] = filtered
            changed = True
    # 移除空的事件列表
    empty_events = [e for e, v in settings['hooks'].items() if not v]
    for e in empty_events:
        del settings['hooks'][e]
        changed = True
    # 如果 hooks 为空，移除整个 hooks 键
    if not settings['hooks']:
        del settings['hooks']
        changed = True
    if changed:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)


def _install_codebuddy(plat_dir, shared_skills, agent_names, agents_meta):
    """安装 CodeBuddy 平台。"""
    ensure_dir(plat_dir)
    # 清理旧版 CEL 文件（处理升级场景）
    _clean_cel_hooks_dir(os.path.join(plat_dir, 'hooks'))
    _clean_cel_agents_dir(os.path.join(plat_dir, 'agents'))
    _clean_cel_skills_dir(os.path.join(plat_dir, 'skills'))
    _clean_legacy_state(plat_dir)
    _clean_cel_hooks_from_settings(os.path.join(plat_dir, 'settings.json'))
    # 部署新版
    _deploy_agents(os.path.join(plat_dir, 'agents'), agent_names, agents_meta, 'codebuddy')
    copy_skill_dir(shared_skills, os.path.join(plat_dir, 'skills', 'convergent-engineering-loop'))


def _install_claude(plat_dir, shared_skills, agent_names, agents_meta):
    """安装 Claude Code 平台。"""
    ensure_dir(plat_dir)
    # 清理旧版 CEL 文件
    _clean_cel_hooks_dir(os.path.join(plat_dir, 'hooks'))
    _clean_cel_agents_dir(os.path.join(plat_dir, 'agents'))
    _clean_cel_skills_dir(os.path.join(plat_dir, 'skills'))
    _clean_legacy_state(plat_dir)
    _clean_cel_hooks_from_settings(os.path.join(plat_dir, 'settings.json'))
    # 部署新版
    _deploy_agents(os.path.join(plat_dir, 'agents'), agent_names, agents_meta, 'claude')
    copy_skill_dir(shared_skills, os.path.join(plat_dir, 'skills', 'convergent-engineering-loop'))


def _install_codex(codex_dir, agents_dir, shared_skills, agent_names, agents_meta):
    """安装 Codex 平台。"""
    ensure_dir(codex_dir)
    # 清理旧版 CEL 文件
    _clean_cel_hooks_dir(os.path.join(codex_dir, 'hooks'))
    _clean_cel_agents_dir(os.path.join(codex_dir, 'agents'))
    _clean_cel_skills_dir(os.path.join(agents_dir, 'skills'))
    _clean_legacy_state(codex_dir)
    _clean_cel_hooks_from_settings(os.path.join(codex_dir, 'hooks.json'))
    # 清理旧版 Codex config.toml 中的 CEL 残留
    _clean_codex_config_toml(os.path.join(codex_dir, 'config.toml'))
    # 部署新版
    _deploy_agents(os.path.join(codex_dir, 'agents'), agent_names, agents_meta, 'codex')
    copy_skill_dir(shared_skills, os.path.join(agents_dir, 'skills', 'convergent-engineering-loop'))


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
        help='将 CEL 安装到指定项目目录（自动清理旧版 hooks 和配置）'
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
