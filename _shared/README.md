# 收敛式工程迭代（CEL）——使用指南

本文档详细描述如何使用 CEL 系统指导项目迭代，覆盖三个平台：CodeBuddy、Codex、Claude Code。

## 前置条件

- **Python 3.8+**：Hook 脚本用 Python 编写，需要系统 PATH 中有 `python` 命令
  - Windows：安装 Python 时勾选 "Add Python to PATH"
  - macOS/Linux：`python3 --version` 可用时，可创建软链接 `sudo ln -s $(which python3) /usr/local/bin/python`
  - 验证：在终端运行 `python --version`，应输出 Python 3.8+
- **Git Bash**（仅 Windows + CodeBuddy 用户）：在 CodeBuddy 设置 → Hooks → 高级设置中，将执行器配置为 `C:\Program Files\Git\bin\bash.exe`

## 系统架构

CEL 由三层组成：

| 层 | 功能 | 执行方式 |
|---|---|---|
| **Skill** | 操作性协议、参考文件、模板、检查清单 | Agent 读取 SKILL.md 后按协议执行 |
| **Hook** | 硬约束自动执行 | 平台在特定事件时自动调用 |
| **Subagent** | 专项推理分析 | Agent 需要时调用 |

## 各平台使用方式

### 一键安装（推荐）

使用 `sync-platforms.py --install` 自动部署到目标项目，与已有配置合并：

```bash
# 单个平台
python scripts/sync-platforms.py --install /path/to/project --platform codebuddy
python scripts/sync-platforms.py --install /path/to/project --platform claude
python scripts/sync-platforms.py --install /path/to/project --platform codex

# 所有平台
python scripts/sync-platforms.py --install /path/to/project --platform all
```

特性：配置合并（保留其他系统 hooks）、升级清理（移除旧版 CEL 文件）、状态保留、幂等。

### 手动安装

#### CodeBuddy

1. **安装**：将 `CodeBuddy/.codebuddy/` 目录复制到项目根目录
   ```bash
   cp -r CodeBuddy/.codebuddy /path/to/your/project/
   ```

2. **Skills 生效**：CodeBuddy 自动加载 `.codebuddy/skills/` 下的技能

3. **Hooks 生效**：`.codebuddy/settings.json` 中配置的 Hook 自动执行
   - 修改文件前：`pre-edit-guard` 检查最小修改原则
   - 执行命令前：`dangerous-command-guard` 拦截危险命令
   - 修改文件后：`post-edit-verify` 提醒验证
   - 修改文件后：`oscillation-detector` 检测震荡

4. **Agents 使用**：`.codebuddy/agents/` 下的 agent 定义在对话中可被调用

5. **Plan 模式**：使用 `references/Plan模式.md` 将 CEL 迭代映射到 Plan 的 todo

#### Codex

1. **安装**：将 `Codex/` 下的两个目录复制到项目根目录
   ```bash
   cp -r Codex/.codex /path/to/your/project/
   cp -r Codex/.agents /path/to/your/project/
   ```

2. **Skills 生效**：Codex 自动加载 `.agents/skills/` 下的技能

3. **Hooks 生效**：`.codex/config.toml` 中配置的 Hook 自动执行

4. **Agents 使用**：`.codex/agents/` 下的 TOML 格式 agent 定义

5. **目标模式**：使用 `references/目标模式.md` 将 CEL 迭代映射到自主目标导向执行

#### Claude Code

1. **安装**：将 `ClaudeCode/.claude/` 目录复制到项目根目录
   ```bash
   cp -r ClaudeCode/.claude /path/to/your/project/
   ```

2. **Skills 生效**：Claude Code 自动加载 `.claude/skills/` 下的技能

3. **Hooks 生效**：`.claude/settings.json` 中配置的 Hook 自动执行
   - Hook 使用 `$CLAUDE_PROJECT_DIR` 环境变量定位脚本

4. **Agents 使用**：`.claude/agents/` 下的 Markdown+YAML 格式 agent 定义

## 迭代流程

### 1. 启动任务

向 Agent 描述任务时，使用以下触发词让 CEL 自动生效：

- "稳妥地做"、"逐步推进" → 加载对应环节参考
- "帮我修这个 bug" → 加载 `代码开发.md` + `测试工程.md`
- "帮我看日志" → 加载 `日志调试.md`
- "处理 review comments" → 加载 `代码审查.md`
- "核对计划与代码" → 加载 `交叉验证.md` + `项目设计.md`
- "修 CI" → 加载 `Harness工程.md`

### 2. 评估轮次

如果不确定当前状态，先进入评估轮次：

```
评估类型：状态评估
当前状态：[描述]
目标状态：[描述]
使用参考：[选择的参考文件]
误差度量：[当前误差值]
误差来源分析：[主要误差来源]
决策：是否需要进入修改轮次
下一步建议：[建议]
```

### 3. 修改轮次

方向明确后进入修改轮次，每轮：

1. 识别当前状态
2. 定义目标完成状态
3. 选择参考文件
4. 定义误差度量
5. **选择最小更新**（只做一个最小修改）
6. 执行更新
7. **外部验证**（运行测试、构建、Lint 等）
8. 比较误差变化
9. 误差下降→接受；上升→回滚
10. 停止条件不满足→继续下一轮

### 4. 停止条件

| 条件类型 | 触发时机 | Agent 行为 |
|---------|---------|-----------|
| 成功停止 | 误差为零、验收标准满足 | 停止并报告完成 |
| 安全停止 | 缺少信息、存在歧义、环境不可用 | 停止并请求用户决策 |
| 震荡停止 | 连续无改进、状态来回切换 | 停止并总结冲突 |

## 参考文件速查

| 任务类型 | 参考文件 | 核心误差维度 |
|---------|---------|------------|
| 需求澄清 | `references/项目设计.md` | 未解决问题、冲突需求、未缓解风险 |
| 架构设计 | `references/架构设计.md` | 未定义模块、接口不清晰、不合理依赖 |
| 代码开发 | `references/代码开发.md` | 失败测试、构建错误、类型/Lint 错误 |
| 文档编写 | `references/文档编写.md` | 过期内容、缺失说明、不可运行示例 |
| 日志调试 | `references/日志调试.md` | 活跃假设、未知信息、复现不确定性 |
| 测试工程 | `references/测试工程.md` | 失败测试、覆盖率缺口、Flaky 测试 |
| 代码审查 | `references/代码审查.md` | 未解决评论、安全/性能/可维护性问题 |
| CI/Harness | `references/Harness工程.md` | Harness 失败、版本漂移、不可复现 |
| 交叉验证 | `references/交叉验证.md` | 标记错误、遗漏、过度实现、语义偏差 |
| Plan 模式 | `references/Plan模式.md` | 未完成 todo、依赖阻塞、验证失败 |
| 目标模式 | `references/目标模式.md` | 子目标误差、全局进度 |

## 模板和检查清单

- **迭代报告**：`templates/迭代报告模板.md` — 记录每轮迭代的完整信息
- **误差度量**：`templates/误差度量模板.md` — 定义和跟踪误差值
- **回滚记录**：`templates/回滚记录模板.md` — 记录回滚原因和后续策略
- **最小修改检查**：`checklists/最小修改检查清单.md` — 确认修改是最小的
- **验证检查**：`checklists/验证检查清单.md` — 确认使用了外部验证
- **停止条件检查**：`checklists/停止条件检查清单.md` — 判断是否应该停止

## Hook 工作原理

Hook 脚本通过 `cel_hook_utils.py` 适配不同平台的输出格式：

```
cel-pre-edit-guard.py  →  from cel_hook_utils import format_deny, format_allow, format_ask, output, is_cel_active, EDIT_TOOLS
                          → CodeBuddy: {"permissionDecision": "deny", "reason": "..."}
                          → Codex:     {"permissionDecision": "deny", "reason": "..."}
                          → Claude:    {"hookSpecificOutput": {"permissionDecision": "deny", ...}}
```

每个平台有自己的 `cel_hook_utils.py`（由 `templates/cel_{platform}_utils.py` 模板生成），输出格式硬编码，不做运行时平台检测。

### CEL 激活检查

所有 Hook 脚本在处理前会调用 `is_cel_active()` 检查 CEL 是否激活：

- **激活**：`cel-state.json` 中 `task.description` 非空 → Hook 正常执行拦截逻辑
- **未激活**：`task.description` 为空 → Hook 直接放行，不干扰其他系统

这意味着 CEL 的 Hook 即使已安装，也不会影响非 CEL 工作流。

### 工具名集合

各平台 `cel_hook_utils.py` 导出精确的平台特定工具名集合：

| 平台 | `EDIT_TOOLS` | `COMMAND_TOOLS` |
|------|-------------|----------------|
| CodeBuddy | `write_to_file`, `replace_in_file` | `execute_command` |
| Claude Code | `edit_file`, `write`, `edit` | `bash`, `shell`, `terminal` |
| Codex | `edit`, `write` | `shell`, `run_command` |

Hook 脚本从 `cel_hook_utils` 导入这些集合，而非硬编码工具名。
