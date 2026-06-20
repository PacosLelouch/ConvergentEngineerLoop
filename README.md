# 收敛式工程迭代（CEL）——多平台系统

将复杂工程任务组织为稳定、可验证、可回滚的小步迭代过程。

## 快速开始

### 方式一：一键安装（推荐）

自动将 CEL 部署到指定项目，自动清理旧版配置：

```bash
# 安装到指定项目（单个平台）
python scripts/sync-platforms.py --install /path/to/your/project --platform codebuddy
python scripts/sync-platforms.py --install /path/to/your/project --platform claude
python scripts/sync-platforms.py --install /path/to/your/project --platform codex

# 安装所有平台
python scripts/sync-platforms.py --install /path/to/your/project --platform all
```

`--install` 模式特性：
- **升级清理**：自动移除旧版 CEL 文件（hooks 脚本、settings 中的 hooks 注册等），避免残留
- **幂等性**：重复执行不会产生重复配置

### 方式二：文件夹包

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

### 方式三：插件包

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
2. 将 `agents/` 复制到 `.codebuddy/agents/`

**Codex** — 复制文件夹包（无原生插件格式）：
```bash
cp -r dist/codex-cel-plugin/.codex /path/to/your/project/
cp -r dist/codex-cel-plugin/.agents /path/to/your/project/
```

## 项目结构

```
_shared/                    # 开发期真源（仅维护用，运行时不依赖）
├── skills/                 # SKILL.md + references/ + templates/ + checklists/
├── agents/                 # 4 个 Agent 指令 + agents.yaml
└── README.md               # 各平台详细使用指南

scripts/
└── sync-platforms.py       # 真源 → 三平台生成脚本

CodeBuddy/                  # CodeBuddy 文件夹包
└── .codebuddy/
    ├── agents/             # Markdown + YAML 格式
    └── skills/             # SKILL.md + references + templates + checklists

Codex/                      # Codex 文件夹包
├── .codex/
│   └── agents/             # TOML 格式（Codex 自动扫描，无需注册）
└── .agents/
    └── skills/             # SKILL.md + references + templates + checklists

ClaudeCode/                 # Claude Code 文件夹包
└── .claude/
    ├── agents/             # Markdown + YAML 格式
    └── skills/             # SKILL.md + references + templates + checklists
```

## 系统概览

### 两层架构

| 层 | 功能 | 执行方式 |
|---|---|---|
| **Skill** | 操作性协议、9+2 参考文件、模板、检查清单 | Agent 读取后按协议执行 |
| **Subagent** | 专项推理分析（4 个） | Agent 需要深度分析时调用 |

两层协同工作流程：

```
用户描述任务
  ↓
┌─── Skill 层 ────────────────────────────────────┐
│ Agent 读取 SKILL.md，按协议选择参考文件和迭代策略  │
│ 通用规则提供命令纪律、编辑纪律、验证纪律、震荡避免  │
└─────────────────────────────────────────────────┘
  ↓
┌─── Subagent 层 ─────────────────────────────────┐
│ cel-planner            规划迭代策略               │
│ cel-test-analyst       分析测试失败根因           │
│ cel-debug-analyst      日志根因分析               │
│ cel-reviewer           评估迭代质量               │
└─────────────────────────────────────────────────┘
```

### Subagent 列表

| Agent | 适用场景 |
|-------|---------|
| `cel-planner` | 规划迭代策略、选择参考文件 |
| `cel-test-analyst` | 分析测试失败根因 |
| `cel-debug-analyst` | 从日志提取根因 |
| `cel-reviewer` | 评估迭代质量、判断停止条件 |

## 使用示例

### 示例 1：修复 Bug

```
用户：帮我修这个 bug —— 运行 pytest 时 test_user_auth 失败了

Agent（CEL 自动生效）：
  → 加载参考：代码开发.md + 测试工程.md
  → 评估轮次：分析失败测试，定位到 auth.py 第 42 行的空值检查缺失
  → 修改轮次 #1：
      迭代轮次：1
      当前状态：test_user_auth 失败（NoneType 错误）
      目标状态：测试通过
      本轮最小更新：在 auth.py:42 添加 None 检查
      验证方式：运行 pytest test_user_auth
      验证结果：测试通过 ✅
      决策：接受修改
  → 停止：误差为零，任务完成
```

### 示例 2：逐步推进重构

```
用户：稳妥地把这个模块从 Class 组件重构为 Hooks，逐步推进

Agent（CEL 自动生效）：
  → 加载参考：代码开发.md
  → 评估轮次：识别 8 个 Class 组件需重构
  → 修改轮次 #1：重构 UserProfile 组件
      验证：npm test 通过 → 接受
  → 修改轮次 #2：重构 Dashboard 组件
      验证：npm test 通过 → 接受
  → ... 每次只重构一个组件 ...
  → 修改轮次 #8：重构最后一个组件 SettingsPanel
      验证：npm test 通过 → 接受
  → 停止：所有组件重构完成，测试全部通过
```

### 示例 3：震荡自检测与回滚

```
Agent 修改轮次 #5：方案 A（添加缓存层）
  验证：性能提升但引入 2 个新 bug → 误差上升 → 回滚

Agent 修改轮次 #6：方案 B（优化查询）
  验证：性能提升，无新 bug → 接受

Agent 修改轮次 #7：又回到方案 A（又添加缓存层）
  Agent 自检震荡：
    → 检测到状态在方案 A/B 间来回切换
    → 停止迭代，总结冲突原因
    → 请求用户决策选择最终方案
```

## 开发和维护

### 修改真源

所有内容维护在 `_shared/` 目录下。修改后运行 sync 生成三平台文件：

```bash
# 生成文件夹包
python scripts/sync-platforms.py --format folders

# 生成插件包
python scripts/sync-platforms.py --format plugins

# 一键安装到项目（推荐，自动清理旧版配置）
python scripts/sync-platforms.py --install /path/to/project --platform codebuddy
python scripts/sync-platforms.py --install /path/to/project --platform all
```

### 修改什么、在哪里改

| 想改的内容 | 修改位置 | sync 后生效位置 |
|-----------|---------|---------------|
| 操作协议、通用规则、停止条件 | `_shared/skills/convergent-engineering-loop/SKILL.md` | 三平台 skills/ |
| 设计背景和理论 | `_shared/skills/convergent-engineering-loop/README.md` | 三平台 skills/ |
| 参考文件（9 种任务类型 + 2 种模式） | `_shared/skills/convergent-engineering-loop/references/*.md` | 三平台 skills/references/ |
| 迭代报告/误差度量/回滚记录模板 | `_shared/skills/convergent-engineering-loop/templates/*.md` | 三平台 skills/templates/ |
| 检查清单 | `_shared/skills/convergent-engineering-loop/checklists/*.md` | 三平台 skills/checklists/ |
| Agent 指令 | `_shared/agents/instructions/*.md` | 三平台 agents/ |
| Agent 元数据 | `_shared/agents/agents.yaml` | 生成时读取 |

### 运行时独立性

删除 `_shared/` 和 `scripts/` 后，`CodeBuddy/`、`Codex/`、`ClaudeCode/` 三个目录仍可独立工作。每个目录拥有完整的 agents、skills、config，运行时零跨目录依赖。

详细使用指南见 `_shared/README.md`。
