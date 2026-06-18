---
name: cel-three-independent-platforms
overview: 将收敛式工程迭代系统拆分为三套完全独立的平台实现（CodeBuddy/Codex/Claude Code），每套可独立运行。_shared/ 仅作为开发期的真源，sync 脚本负责生成各平台文件，运行时零跨目录依赖。
todos:
  - id: create-shared-dir
    content: 创建 _shared/ 目录结构和真源文件（skills/ + hooks/ + agents/ + templates/）
    status: completed
  - id: create-hook-utils
    content: 创建三平台 hook_utils.py 真源（_shared/hooks/templates/）
    status: completed
    dependencies:
      - create-shared-dir
  - id: create-hook-scripts
    content: 创建 4 个 Hook 主脚本（_shared/hooks/），通过 from hook_utils import 适配输出
    status: completed
    dependencies:
      - create-hook-utils
  - id: create-sync-script
    content: 创建 scripts/sync-platforms.py，读取 _shared/ 生成三平台完整文件
    status: completed
    dependencies:
      - create-hook-scripts
  - id: create-platform-configs
    content: 创建三平台配置文件（.codebuddy/settings.json, .codex/config.toml, .claude/settings.json）
    status: completed
    dependencies:
      - create-sync-script
  - id: create-subagents
    content: 创建 4 个 Agent 指令真源 + agents.yaml，sync 生成三平台格式
    status: completed
    dependencies:
      - create-sync-script
  - id: clean-skill-md
    content: 精简 SKILL.md：移除 Banach 理论，增加自动化支持段落
    status: completed
    dependencies:
      - create-shared-dir
---

## 提供用户需求

1. **清理 SKILL.md**：移除背景理论（Banach 不动点思想、数学公式、设计哲学说明），只保留操作性描述；移除的背景内容放到 README.md
2. **Skill/Hook/Subagent 分工**：识别 SKILL.md 中哪些内容应做成 Hook（硬约束自动执行）或 Subagent（专项推理分析）
3. **三平台独立实现**：CodeBuddy（`.codebuddy/`）、Codex（`.codex/`）、Claude Code（`.claude/`）各有一套**完全独立、可单独运行**的系统。每个平台目录包含自己完整的 hooks、agents、skills、config，不依赖任何外部目录

## 产品概述

将纯 Skill 架构的收敛式工程迭代系统，重构为 Skill + Hook + Subagent 三层架构。三平台各自拥有完整的独立副本，运行时零跨目录依赖。`_shared/` 仅作为开发期真源，通过 `sync-platforms.py` 生成三份副本，即使删掉 `_shared/` 各平台仍可正常工作。

## 核心功能

- SKILL.md 精简：仅保留操作性协议，背景理论迁移至 README.md
- Hook 实现：修改前守卫、危险命令拦截、修改后验证、震荡检测
- Subagent 实现：收敛计划、测试分析、日志调试、代码审查
- 三平台独立：每个平台目录自包含（hooks + agents + skills + config + state），运行时无外部依赖
- 冗余管理：`_shared/` 真源 + `sync-platforms.py` 一键同步三份

## 技术栈

- 技能文档：Markdown
- Hook 脚本：Python 3（标准库 only：json, sys, os, re）
- CodeBuddy Hooks：`.codebuddy/hooks/*.py` + `.codebuddy/settings.json`
- CodeBuddy Agents：Markdown + YAML frontmatter（`.codebuddy/agents/`）
- Codex Hooks：`.codex/hooks/*.py` + `.codex/config.toml`
- Codex Agents：TOML（`.codex/agents/`）
- Claude Hooks：`.claude/hooks/*.py` + `.claude/settings.json`
- Claude Agents：Markdown + YAML frontmatter（`.claude/agents/`）
- 同步脚本：Python 3（`scripts/sync-platforms.py`）

## 架构原则

**每个平台目录完全自包含，运行时零外部依赖。使用时将对应平台目录下的内容复制到项目根目录。**

```
开发期真源                  同步脚本              三套独立运行时（各包一层目录）
_shared/               sync-platforms.py        
├── hooks/         ──────────────────────→   CodeBuddy/
├── agents/        ──────────────────────→     └── .codebuddy/
├── skills/        ──────────────────────→         ├── hooks/
└── agents.yaml    ──────────────────────→         ├── agents/
                                                  ├── skills/
                                                  ├── settings.json
                                                  └── cel-state.json

                                              Codex/
                                                ├── .codex/
                                                │   ├── hooks/
                                                │   ├── agents/
                                                │   ├── config.toml
                                                │   └── cel-state.json
                                                └── .agents/
                                                    └── skills/

                                              ClaudeCode/
                                                └── .claude/
                                                    ├── hooks/
                                                    ├── agents/
                                                    ├── skills/
                                                    ├── settings.json
                                                    └── cel-state.json
```

关键设计：

- **每个平台包一层目录**（CodeBuddy/、Codex/、ClaudeCode/），使用时将目录下的 dot-dir 复制到项目根目录
- **Codex 特殊**：skills 在 `.agents/skills/`（Codex 标准路径），hooks 和 agents 在 `.codex/`
- **Hook 脚本主体完全相同**（检测逻辑一致），通过 `from hook_utils import ...` 调用平台特定的输出格式函数
- **`hook_utils.py` 是唯一平台差异文件**：CodeBuddy 版输出 CodeBuddy JSON 格式，Codex 版输出 Codex 格式，Claude 版输出 Claude 格式（含 `hookSpecificOutput` 包装）
- **删除 `_shared/` 和 `scripts/` 后，三套系统仍可独立运行**

## 实现方案

### 一、SKILL.md 内容分层

| 内容 | 归属 | 理由 |
| --- | --- | --- |
| Banach 公式 + 借鉴说明 | **README.md** | 背景理论 |
| 何时使用 / 轮次类型 / 执行协议 | 保留 Skill | 操作性 |
| 通用规则（可自动执行部分） | **Hook** | 硬约束 |
| 通用规则（指导性部分） | 保留 Skill | 指导 |
| 震荡停止 | **Hook** | 自动检测 |


### 二、Hook 脚本设计

#### 冗余消除策略

Hook 脚本分两层：

1. **主脚本**（4 个，三平台完全相同）：`pre-edit-guard.py`、`dangerous-command-guard.py`、`post-edit-verify.py`、`oscillation-detector.py`

- 包含所有检测逻辑
- 通过 `from hook_utils import format_deny, format_allow, format_ask, format_additional_context` 调用输出格式
- Python 运行时自动将脚本所在目录加入 `sys.path`，`from hook_utils import ...` 可正常工作

2. **`hook_utils.py`**（3 份，各平台不同）：

- `.codebuddy/hooks/hook_utils.py` → 输出 CodeBuddy 格式
- `.codex/hooks/hook_utils.py` → 输出 Codex 格式
- `.claude/hooks/hook_utils.py` → 输出 Claude Code 格式

这样只需维护一份主脚本逻辑 + 三份小型格式适配器。

#### hook_utils.py 各平台差异

**CodeBuddy 版**（`permissionDecision` 顶层字段，支持 allow/deny/ask）：

```python
def format_deny(reason):
    return {"permissionDecision": "deny", "reason": reason}

def format_allow(reason=""):
    result = {"permissionDecision": "allow"}
    if reason: result["reason"] = reason
    return result

def format_ask(reason):
    return {"permissionDecision": "ask", "reason": reason}

def format_additional_context(context):
    return {"additionalContext": context}

STATE_FILE = os.path.join(os.environ.get('CODEBUDDY_PROJECT_DIR', '.'), '.codebuddy', 'cel-state.json')
```

**Codex 版**（`permissionDecision` 顶层字段，不支持 ask，降级为 deny）：

```python
def format_deny(reason):
    return {"permissionDecision": "deny", "reason": reason}

def format_allow(reason=""):
    result = {"permissionDecision": "allow"}
    if reason: result["reason"] = reason
    return result

def format_ask(reason):
    # Codex 不支持 ask，降级为 deny
    return {"permissionDecision": "deny", "reason": f"[需用户确认] {reason}"}

def format_additional_context(context):
    return {"additionalContext": context}

STATE_FILE = os.path.join(os.getcwd(), '.codex', 'cel-state.json')
```

**Claude 版**（`hookSpecificOutput` 包装，支持 allow/deny/ask，用 `systemMessage` 注入上下文）：

```python
def _wrap(decision, reason="", hook_event="PreToolUse"):
    result = {"hookSpecificOutput": {"hookEventName": hook_event, "permissionDecision": decision}}
    if reason: result["hookSpecificOutput"]["permissionDecisionReason"] = reason
    return result

def format_deny(reason):
    return _wrap("deny", reason)

def format_allow(reason=""):
    return _wrap("allow", reason)

def format_ask(reason):
    return _wrap("ask", reason)

def format_additional_context(context):
    return {"systemMessage": context, "hookSpecificOutput": {"hookEventName": "PostToolUse", "permissionDecision": "allow"}}

STATE_FILE = os.path.join(os.environ.get('CLAUDE_PROJECT_DIR', '.'), '.claude', 'cel-state.json')
```

#### 各平台 Hook 配置（指向自己的 hooks/ 目录）

**CodeBuddy** (`CodeBuddy/.codebuddy/settings.json`)：

```
"command": "python3 \"$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/pre-edit-guard.py\""
```

**Codex** (`Codex/.codex/config.toml`)：

```
command = "python3 .codex/hooks/pre-edit-guard.py"
```

**Claude** (`ClaudeCode/.claude/settings.json`)：

```
"command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/pre-edit-guard.py\""
```

### 三、Subagent 实现（各平台格式不同，内容相同）

| 平台 | 格式 | 路径 |
| --- | --- | --- |
| CodeBuddy | Markdown + YAML frontmatter | `.codebuddy/agents/*.md` |
| Codex | TOML | `.codex/agents/*.toml` |
| Claude | Markdown + YAML frontmatter | `.claude/agents/*.md` |


4 个 Subagent：convergence-planner、test-failure-analyst、debug-root-cause-analyst、review-convergence-agent

### 四、sync-platforms.py 设计

读取 `_shared/` 真源，支持两种输出格式：

```
python scripts/sync-platforms.py --format folders    # 生成文件夹包（默认）
python scripts/sync-platforms.py --format plugins    # 生成插件包
```

#### 模式一：文件夹包（folders）

生成三个平台目录，每个包含 dot-dirs，使用时复制到项目根目录：

| 真源 | 生成目标 | 方式 |
| --- | --- | --- |
| `_shared/hooks/*.py`（除 hook_utils.py） | 三平台 `hooks/` 目录 | 直接复制 |
| `_shared/hooks/templates/codebuddy_utils.py` | `CodeBuddy/.codebuddy/hooks/hook_utils.py` | 复制 |
| `_shared/hooks/templates/codex_utils.py` | `Codex/.codex/hooks/hook_utils.py` | 复制 |
| `_shared/hooks/templates/claude_utils.py` | `ClaudeCode/.claude/hooks/hook_utils.py` | 复制 |
| `_shared/agents/instructions/*.md` + `agents.yaml` | 三平台 `agents/` 目录 | 读取 → 生成 Markdown/TOML |
| `_shared/skills/convergent-engineering-loop/` | `CodeBuddy/.codebuddy/skills/` + `Codex/.agents/skills/` + `ClaudeCode/.claude/skills/` | 复制 |


#### 模式二：插件包（plugins）

生成各平台原生插件格式，安装后自动生效：

**Claude Code 插件**（一体化，最完善）：

```
dist/claude-cel-plugin/
├── .claude-plugin/
│   └── plugin.json                    # { name, description, version }
├── skills/
│   └── convergent-engineering-loop/
│       ├── SKILL.md
│       ├── references/
│       ├── templates/
│       └── checklists/
├── hooks/
│   ├── pre-edit-guard.py
│   ├── dangerous-command-guard.py
│   ├── post-edit-verify.py
│   ├── oscillation-detector.py
│   └── hook_utils.py                  # 仅 Claude 版
├── agents/
│   ├── convergence-planner.md
│   ├── test-failure-analyst.md
│   ├── debug-root-cause-analyst.md
│   └── review-convergence-agent.md
└── marketplace.json                   # { name, owner, plugins: [...] }
```

安装方式：`/plugin marketplace add ./dist/claude-cel-plugin` 或推到 GitHub 后从远程安装

**CodeBuddy 插件**（Skills ZIP + 辅助配置）：

```
dist/codebuddy-cel-plugin/
├── convergent-engineering-loop.zip    # Skills ZIP（含 SKILL.md + references + templates + checklists）
├── settings-hooks.json               # Hooks 配置片段（用户需合并到 .codebuddy/settings.json）
└── agents/                            # Agent 定义（用户需复制到 .codebuddy/agents/）
    ├── convergence-planner.md
    ├── test-failure-analyst.md
    ├── debug-root-cause-analyst.md
    └── review-convergence-agent.md
```

安装方式：设置 → Skills → 导入 ZIP；hooks/agents 需手动配置

**Codex 插件**（无原生插件格式，仍为文件夹包）：

```
dist/codex-cel-plugin/                # 与 folders 模式的 Codex/ 目录相同
├── .codex/
└── .agents/
```

安装方式：复制到项目根目录

生成物头部标注：`# 由 sync-platforms.py 自动生成，修改请改 _shared/ 下的真源`

## 目录结构

```
README.md                                      # 根目录说明：如何生成/更新三平台、如何使用

_shared/                                       # 开发期真源（仅维护用，运行时不依赖）
├── README.md                                  # 各平台使用指南：如何用这套系统指导项目迭代
├── skills/
│   └── convergent-engineering-loop/
│       ├── SKILL.md                           # 精简后的操作性协议
│       ├── README.md                          # 设计与背景文档
│       ├── references/                        # 各环节参考文件（11 个）
│       │   ├── 项目设计.md
│       │   ├── 架构设计.md
│       │   ├── 代码开发.md
│       │   ├── 测试工程.md
│       │   ├── 日志调试.md
│       │   ├── 代码审查.md
│       │   ├── 文档编写.md
│       │   ├── 交叉验证.md
│       │   ├── 目标模式.md
│       │   ├── Plan模式.md
│       │   └── Harness工程.md
│       ├── templates/                         # 迭代报告等模板（3 个）
│       │   ├── 迭代报告模板.md
│       │   ├── 误差度量模板.md
│       │   └── 回滚记录模板.md
│       └── checklists/                        # 检查清单（3 个）
│           ├── 停止条件检查清单.md
│           ├── 最小修改检查清单.md
│           └── 验证检查清单.md
├── hooks/
│   ├── pre-edit-guard.py                      # 修改前守卫（三平台共用逻辑）
│   ├── dangerous-command-guard.py             # 危险命令拦截
│   ├── post-edit-verify.py                    # 修改后验证提醒
│   ├── oscillation-detector.py                # 震荡检测
│   └── templates/                             # 各平台 hook_utils.py 真源
│       ├── codebuddy_utils.py                 # CodeBuddy 输出格式
│       ├── codex_utils.py                     # Codex 输出格式
│       └── claude_utils.py                    # Claude 输出格式
├── agents/
│   ├── instructions/                          # 纯 Markdown 指令（平台无关）
│   │   ├── convergence-planner.md
│   │   ├── test-failure-analyst.md
│   │   ├── debug-root-cause-analyst.md
│   │   └── review-convergence-agent.md
│   └── agents.yaml                            # 元数据
└── cel-state-schema.json                      # 状态文件结构定义

scripts/
└── sync-platforms.py                          # 读取 _shared/ → 生成三平台完整文件
                                            # --format folders → CodeBuddy/ Codex/ ClaudeCode/
                                            # --format plugins → dist/ 下的插件包

# ===== 三套独立系统（每个平台包一层目录，完全自包含）=====
# 使用时将对应平台目录下的所有内容复制到项目根目录即可

CodeBuddy/                                     # CodeBuddy IDE 完整配置
└── .codebuddy/                                # 复制到项目根目录即可生效
    ├── settings.json                          # Hook 配置
    ├── hooks/                                 # CodeBuddy 专属 hook 脚本
    │   ├── pre-edit-guard.py
    │   ├── dangerous-command-guard.py
    │   ├── post-edit-verify.py
    │   ├── oscillation-detector.py
    │   └── hook_utils.py                      # CodeBuddy 输出格式（硬编码）
    ├── agents/                                # CodeBuddy subagent（Markdown+YAML）
    │   ├── convergence-planner.md
    │   ├── test-failure-analyst.md
    │   ├── debug-root-cause-analyst.md
    │   └── review-convergence-agent.md
    ├── skills/convergent-engineering-loop/
    │   ├── SKILL.md
    │   ├── references/                        # 11 个参考文件
    │   ├── templates/                         # 3 个模板文件
    │   └── checklists/                        # 3 个检查清单
    └── cel-state.json                         # 迭代状态

Codex/                                         # Codex CLI 完整配置
├── .codex/                                    # 复制到项目根目录：hooks + agents + config
│   ├── config.toml                            # agents + hooks 配置
│   ├── hooks/                                 # Codex 专属 hook 脚本
│   │   ├── pre-edit-guard.py
│   │   ├── dangerous-command-guard.py
│   │   ├── post-edit-verify.py
│   │   ├── oscillation-detector.py
│   │   └── hook_utils.py                      # Codex 输出格式（硬编码）
│   ├── agents/                                # Codex subagent（TOML）
│   │   ├── convergence-planner.toml
│   │   ├── test-failure-analyst.toml
│   │   ├── debug-root-cause-analyst.toml
│   │   └── review-convergence-agent.toml
│   └── cel-state.json                         # 迭代状态
└── .agents/                                   # 复制到项目根目录：Codex skills 标准路径
    └── skills/convergent-engineering-loop/
        ├── SKILL.md
        ├── references/                        # 11 个参考文件
        ├── templates/                         # 3 个模板文件
        └── checklists/                        # 3 个检查清单

ClaudeCode/                                    # Claude Code 完整配置
└── .claude/                                   # 复制到项目根目录即可生效
    ├── settings.json                          # Hook 配置
    ├── hooks/                                 # Claude 专属 hook 脚本
    │   ├── pre-edit-guard.py
    │   ├── dangerous-command-guard.py
    │   ├── post-edit-verify.py
    │   ├── oscillation-detector.py
    │   └── hook_utils.py                      # Claude 输出格式（硬编码）
    ├── agents/                                # Claude subagent（Markdown+YAML）
    │   ├── convergence-planner.md
    │   ├── test-failure-analyst.md
    │   ├── debug-root-cause-analyst.md
    │   └── review-convergence-agent.md
    ├── skills/convergent-engineering-loop/
    │   ├── SKILL.md
    │   ├── references/                        # 11 个参考文件
    │   ├── templates/                         # 3 个模板文件
    │   └── checklists/                        # 3 个检查清单
    └── cel-state.json                         # 迭代状态

# ===== 插件包（由 sync-platforms.py --format plugins 生成）=====

dist/
├── claude-cel-plugin/                        # Claude Code 一体化插件
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── skills/convergent-engineering-loop/   # SKILL.md + references + templates + checklists
│   ├── hooks/                                # 4 个 Hook + hook_utils.py（Claude 版）
│   ├── agents/                               # 4 个 Markdown+YAML agent
│   └── marketplace.json
├── codebuddy-cel-plugin/                     # CodeBuddy Skills ZIP + 辅助配置
│   ├── convergent-engineering-loop.zip       # Skills ZIP
│   ├── settings-hooks.json                   # Hooks 配置片段
│   └── agents/                               # Agent 定义
└── codex-cel-plugin/                         # Codex 文件夹包（无原生插件格式）
    ├── .codex/                               # 同 folders 模式
    └── .agents/
```

## 实现备注

- **运行时独立性**：删除 `_shared/` 和 `scripts/` 后，三个平台目录仍可正常工作——每个目录有自己的 hooks、agents、skills、config、state
- **冗余消除**：Hook 主脚本检测逻辑三平台完全相同，仅 `hook_utils.py` 不同（~30行/平台）。`sync-platforms.py` 从 `_shared/hooks/` 复制主脚本 + 从 `_shared/hooks/templates/` 复制对应格式文件
- **环境变量仅用于路径解析**（找项目根目录），**不用于平台检测**——平台身份由文件物理位置（`from hook_utils import ...`）硬确定
- Hook 脚本使用 Python3 标准库，不引入外部依赖
- Windows 兼容性：Codex config.toml 支持 `commandWindows` 字段；CodeBuddy/Claude 用 `"$CODEBUDDY_PROJECT_DIR"/"$CLAUDE_PROJECT_DIR"` 变量
- Agent 指令维护：修改 `_shared/agents/instructions/` + `agents.yaml`，运行 sync 后三平台同步
- 震荡检测状态：每个平台在自己的 `cel-state.json` 中维护，路径由 `hook_utils.py` 中的 `STATE_FILE` 变量确定
- Post-edit-verify 不自动运行验证命令，通过 `format_additional_context` 提醒 Agent 执行验证
- Rollback Hook 暂不实现（自动 git restore 有破坏性风险）