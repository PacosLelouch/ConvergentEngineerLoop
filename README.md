# 收敛式工程迭代（CEL）——多平台系统

将复杂工程任务组织为稳定、可验证、可回滚的小步迭代过程。

## 快速开始

### 方式一：文件夹包

选择你的平台，将对应目录下的文件复制到项目根目录：

```bash
# CodeBuddy 用户
cp -r CodeBuddy/.codebuddy /path/to/your/project/

# Codex 用户
cp -r Codex/.codex /path/to/your/project/
cp -r Codex/.agents /path/to/your/project/

# Claude Code 用户
cp -r ClaudeCode/.claude /path/to/your/project/
```

### 方式二：插件包

```bash
# 先生成插件包
python scripts/sync-platforms.py --format plugins
```

**Claude Code** — 一体化插件，安装后自动生效：
```
/plugin marketplace add ./dist/claude-cel-plugin
```

**CodeBuddy** — Skills ZIP 导入 + 手动配置：
1. 设置 → Skills → 导入 `dist/codebuddy-cel-plugin/convergent-engineering-loop.zip`
2. 将 `settings-hooks.json` 内容合并到 `.codebuddy/settings.json`
3. 将 `agents/` 复制到 `.codebuddy/agents/`

**Codex** — 复制文件夹包（无原生插件格式）：
```bash
cp -r dist/codex-cel-plugin/.codex /path/to/your/project/
cp -r dist/codex-cel-plugin/.agents /path/to/your/project/
```

## 项目结构

```
_shared/                    # 开发期真源（仅维护用，运行时不依赖）
├── skills/                 # SKILL.md + references/ + templates/ + checklists/
├── hooks/                  # 4 个 Hook 主脚本 + templates/（三平台 utils）
├── agents/                 # 4 个 Agent 指令 + agents.yaml
├── cel-state-schema.json   # 状态文件 JSON Schema
└── README.md               # 各平台详细使用指南

scripts/
└── sync-platforms.py       # 真源 → 三平台生成脚本

CodeBuddy/                  # CodeBuddy 文件夹包
└── .codebuddy/
    ├── hooks/              # Hook 脚本 + hook_utils.py（CodeBuddy 版）
    ├── agents/             # Markdown + YAML 格式
    ├── skills/             # SKILL.md + references + templates + checklists
    ├── settings.json       # Hook 配置
    └── cel-state.json      # 初始状态

Codex/                      # Codex 文件夹包
├── .codex/
│   ├── hooks/              # Hook 脚本 + hook_utils.py（Codex 版）
│   ├── agents/             # TOML 格式
│   ├── config.toml         # Agent + Hook 配置
│   └── cel-state.json      # 初始状态
└── .agents/
    └── skills/             # SKILL.md + references + templates + checklists

ClaudeCode/                 # Claude Code 文件夹包
└── .claude/
    ├── hooks/              # Hook 脚本 + hook_utils.py（Claude 版）
    ├── agents/             # Markdown + YAML 格式
    ├── skills/             # SKILL.md + references + templates + checklists
    ├── settings.json       # Hook 配置
    └── cel-state.json      # 初始状态
```

## 开发和维护

### 修改真源

所有内容维护在 `_shared/` 目录下。修改后运行 sync 生成三平台文件：

```bash
# 生成文件夹包
python scripts/sync-platforms.py --format folders

# 生成插件包
python scripts/sync-platforms.py --format plugins

# 同时生成两种
python scripts/sync-platforms.py --format folders
python scripts/sync-platforms.py --format plugins
```

### 修改什么、在哪里改

| 想改的内容 | 修改位置 | sync 后生效位置 |
|-----------|---------|---------------|
| 操作协议、通用规则、停止条件 | `_shared/skills/convergent-engineering-loop/SKILL.md` | 三平台 skills/ |
| 设计背景和理论 | `_shared/skills/convergent-engineering-loop/README.md` | 三平台 skills/ |
| 参考文件（9 种任务类型 + 2 种模式） | `_shared/skills/convergent-engineering-loop/references/*.md` | 三平台 skills/references/ |
| 迭代报告/误差度量/回滚记录模板 | `_shared/skills/convergent-engineering-loop/templates/*.md` | 三平台 skills/templates/ |
| 检查清单 | `_shared/skills/convergent-engineering-loop/checklists/*.md` | 三平台 skills/checklists/ |
| Hook 检测逻辑 | `_shared/hooks/*.py`（主脚本） | 三平台 hooks/ |
| Hook 输出格式 | `_shared/hooks/templates/*_utils.py` | 对应平台 hooks/hook_utils.py |
| Agent 指令 | `_shared/agents/instructions/*.md` | 三平台 agents/ |
| Agent 元数据 | `_shared/agents/agents.yaml` | 生成时读取 |

### 运行时独立性

删除 `_shared/` 和 `scripts/` 后，`CodeBuddy/`、`Codex/`、`ClaudeCode/` 三个目录仍可独立工作。每个目录拥有完整的 hooks、agents、skills、config、state，运行时零跨目录依赖。

## 系统概览

### 三层架构

| 层 | 功能 | 执行方式 |
|---|---|---|
| **Skill** | 操作性协议、9+2 参考文件、模板、检查清单 | Agent 读取后按协议执行 |
| **Hook** | 硬约束自动执行（4 个） | 平台在工具调用前后自动触发 |
| **Subagent** | 专项推理分析（4 个） | Agent 需要深度分析时调用 |

### Hook 列表

| Hook | 触发时机 | 作用 |
|------|---------|------|
| `pre-edit-guard` | 文件修改前 | 检查最小修改原则、防止测试削弱 |
| `dangerous-command-guard` | 命令执行前 | 拦截破坏性命令 |
| `post-edit-verify` | 文件修改后 | 注入验证提醒 |
| `oscillation-detector` | 文件修改后 | 检测震荡并阻止循环 |

### Subagent 列表

| Agent | 适用场景 |
|-------|---------|
| `convergence-planner` | 规划迭代策略、选择参考文件 |
| `test-failure-analyst` | 分析测试失败根因 |
| `debug-root-cause-analyst` | 从日志提取根因 |
| `review-convergence-agent` | 评估迭代质量、判断停止条件 |

详细使用指南见 `_shared/README.md`。
