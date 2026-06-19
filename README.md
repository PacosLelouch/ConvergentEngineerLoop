# 收敛式工程迭代（CEL）——多平台系统

将复杂工程任务组织为稳定、可验证、可回滚的小步迭代过程。

## 前置条件

- **Python 3.8+**：Hook 脚本用 Python 编写，需要系统 PATH 中有 `python` 命令
  - Windows：安装 [Python](https://www.python.org/downloads/) 时勾选 "Add Python to PATH"
  - macOS/Linux：`python3 --version` 可用时，可创建软链接 `sudo ln -s $(which python3) /usr/local/bin/python`
  - 验证：在终端运行 `python --version`，应输出 Python 3.8+
- **Git Bash**（仅 Windows + CodeBuddy 用户）：在 CodeBuddy 设置 → Hooks → 高级设置中，将执行器配置为 `C:\Program Files\Git\bin\bash.exe`

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

## 系统概览

### 三层架构

| 层 | 功能 | 执行方式 |
|---|---|---|
| **Skill** | 操作性协议、9+2 参考文件、模板、检查清单 | Agent 读取后按协议执行 |
| **Hook** | 硬约束自动执行（4 个） | 平台在工具调用前后自动触发 |
| **Subagent** | 专项推理分析（4 个） | Agent 需要深度分析时调用 |

三层协同工作流程：

```
用户描述任务
  ↓
┌─── Skill 层 ────────────────────────────────────┐
│ Agent 读取 SKILL.md，按协议选择参考文件和迭代策略  │
└─────────────────────────────────────────────────┘
  ↓
┌─── Hook 层 ─────────────────────────────────────┐
│ 修改前：pre-edit-guard 检查最小修改原则           │
│ 命令前：dangerous-command-guard 拦截破坏性命令     │
│ 修改后：post-edit-verify 注入验证提醒             │
│ 修改后：oscillation-detector 检测震荡             │
└─────────────────────────────────────────────────┘
  ↓
┌─── Subagent 层 ─────────────────────────────────┐
│ convergence-planner    规划迭代策略               │
│ test-failure-analyst   分析测试失败根因           │
│ debug-root-cause-analyst 日志根因分析             │
│ review-convergence-agent 评估迭代质量             │
└─────────────────────────────────────────────────┘
```

### Hook 列表

| Hook | 触发时机 | 作用 | 拦截方式 |
|------|---------|------|---------|
| `pre-edit-guard` | 文件修改前 | 检查最小修改原则、防止测试削弱 | deny（阻止修改） |
| `dangerous-command-guard` | 命令执行前 | 拦截破坏性命令（force push、rm -rf 等） | deny（阻止命令） |
| `post-edit-verify` | 文件修改后 | 注入验证提醒（建议运行测试/Lint 等） | additionalContext（不阻止） |
| `oscillation-detector` | 文件修改后 | 检测震荡（连续无改进、状态来回切换） | deny（阻止继续） |

### Subagent 列表

| Agent | 适用场景 |
|-------|---------|
| `convergence-planner` | 规划迭代策略、选择参考文件 |
| `test-failure-analyst` | 分析测试失败根因 |
| `debug-root-cause-analyst` | 从日志提取根因 |
| `review-convergence-agent` | 评估迭代质量、判断停止条件 |

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

**Hook 在此过程中的作用**：
- `pre-edit-guard`：确认只修改了 auth.py 一处，没有误改其他文件
- `post-edit-verify`：提醒运行 `pytest test_user_auth` 验证
- `oscillation-detector`：确认没有震荡（每轮都有改进）

### 示例 2：逐步推进重构

```
用户：稳妥地把这个模块从 Class 组件重构为 Hooks，逐步推进

Agent（CEL 自动生效）：
  → 加载参考：代码开发.md
  → 评估轮次：识别 8 个 Class 组件需重构
  → 修改轮次 #1：重构 UserProfile 组件
      pre-edit-guard：✅ 只修改了 UserProfile 相关文件
      验证：npm test 通过 → 接受
  → 修改轮次 #2：重构 Dashboard 组件
      pre-edit-guard：✅ 只修改了 Dashboard 相关文件
      验证：npm test 通过 → 接受
  → ... 每次只重构一个组件 ...
  → 修改轮次 #8：重构最后一个组件 SettingsPanel
      验证：npm test 通过 → 接受
  → 停止：所有组件重构完成，测试全部通过
```

### 示例 3：危险命令拦截

```
Agent 尝试执行：git push --force

dangerous-command-guard 触发：
  → 检测到 force push 命令
  → 返回 deny，原因："禁止 force push，可能覆盖远程提交"
  → Agent 收到拒绝，改为使用安全的 git push
```

### 示例 4：震荡检测与回滚

```
Agent 修改轮次 #5：方案 A（添加缓存层）
  验证：性能提升但引入 2 个新 bug → 误差上升 → 回滚

Agent 修改轮次 #6：方案 B（优化查询）
  验证：性能提升，无新 bug → 接受

Agent 修改轮次 #7：又回到方案 A（又添加缓存层）
  oscillation-detector 触发：
    → 检测到状态在方案 A/B 间来回切换
    → 返回 deny，阻止继续循环
    → 建议用户决策选择最终方案
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

## 故障排查

### Hook 未执行

1. **确认 Python 可用**：在终端运行 `python --version`，确保输出 Python 3.8+
2. **CodeBuddy Windows 用户**：在设置 → Hooks → 高级设置中配置执行器为 Git Bash（如 `C:\Program Files\Git\bin\bash.exe`）
3. **确认 Hook 配置存在**：检查 `.codebuddy/settings.json` / `.claude/settings.json` / `.codex/config.toml` 中的 hooks 配置
4. **查看 Hook 日志**：CodeBuddy 插件设置中有 Hooks 选项卡，可查看执行日志和错误信息

### Hook 执行报错

- `python: command not found`：Python 未加入系统 PATH，参考[前置条件](#前置条件)
- `ModuleNotFoundError`：确保 `hook_utils.py` 与其他 hook 脚本在同一目录
- JSON 解析错误：Hook 脚本通过 stdin 接收输入、stdout 输出 JSON，确保没有额外的 print 语句干扰输出

详细使用指南见 `_shared/README.md`。
