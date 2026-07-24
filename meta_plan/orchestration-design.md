# CEL 自我测试 —— Agent 编排方案

> **2026-07-24 实现说明**：本文后续的 `task_list`、agent 自报 metrics、共享
> `working/` 和 T01→T15 编排均为历史设计，不是当前可执行规范。当前唯一任务源是
> `cel-eval-mock-project/task_suite.json` 的 `primary`；隔离规范见
> `meta_plan/experiment-isolation.md`，执行方式见
> `cel-eval-mock-project/harness/README.md`。旧段落仅保留用于设计沿革追溯。

> 由主 Agent 作为编排者，按照任务测例逐个 spawn worker agent，在 CEL/非CEL 两种条件下分别执行，采集指标、对比分析、落盘报告。这是 CEL 系统**用自身协议测试自身有效性**的元循环验证。

---

## 一、目录结构设计

### 1.1 测试输出目录 `test-runs/`

```
test-runs/
├── README.md                              # 目录说明
├── run_config.yaml                        # 编排主配置文件（见第二节）
└── codex_claude-4.5_2026-07-21T143052Z/  # 一次实验运行
    ├── manifest.yaml                      # 本次运行的元信息
    ├── report.md                          # 任务级聚合报告（主 Agent 生成）
    ├── T01/
    │   ├── control/
    │   │   ├── session.yaml               # worker 会话元信息
    │   │   ├── metrics.yaml               # 采集的指标
    │   │   ├── agent_log.md               # worker 完整对话日志
    │   │   └── git_diff.patch             # 修改 diff
    │   └── cel/
    │       ├── session.yaml
    │       ├── metrics.yaml
    │       ├── agent_log.md
    │       └── git_diff.patch
    ├── T02/
    │   ├── control/
    │   └── cel/
    └── ...
```

### 1.2 命名规范

| 元素 | 格式 | 示例 |
|------|------|------|
| 运行目录 | `{platform}_{model}_{ISO8601_timestamp}` | `codex_claude-4.5_2026-07-21T143052Z` |
| 任务目录 | `T{两位编号}` | `T01`, `T14` |
| 分组目录 | `control` 或 `cel` | — |
| 会话元信息 | `session.yaml` | — |
| 指标文件 | `metrics.yaml` | — |
| 对话日志 | `agent_log.md` | — |
| diff 文件 | `git_diff.patch` | — |

---

## 二、编排主配置文件 `run_config.yaml`

主 Agent 启动时读取此文件，决定本次测试的参数。

```yaml
# ============================================================
# CEL A/B 测试编排配置
# 主 Agent 读取此文件，按 task_list 顺序串行执行
# ============================================================

# --- 本次运行的元信息 ---
run:
  platform: codebuddy         # 目标平台：codebuddy | codex | claude-code
  model: claude-4.5           # 固定模型版本
  task_suite: T01-T15         # 要执行的任务范围标识

# --- mock 项目路径 ---
project:
  mock_repo_path: "../cel-eval-mock-project"
  task_init_branch_format: "task/{task_id}-init"    # 任务初始状态的 git branch 格式
  task_expected_branch_format: "task/{task_id}-expected"  # 任务预期完成态 branch

# --- 任务列表（按此顺序串行执行） ---
task_list:
  - id: T01
    domain: 代码开发
    complexity: simple
    max_rounds: 10
    task_description: |
      `src/user_service.py` 中 `get_user_by_id` 函数在传入不存在的 user_id 时
      抛出 `NoneTypeError`（第 42 行访问 `user.name`），请修复它。

    success_condition:
      test_passes: "test_get_user_not_found"
      max_files_changed: 2
      required_file_pattern: "src/user_service.py"

  - id: T02
    domain: 代码开发
    complexity: medium
    max_rounds: 20
    task_description: |
      `src/payment.py` 的 `process_payment` 函数在扣款成功后调用
      `src/notification.py` 的 `send_receipt`。但 `send_receipt` 需要
      `user_email` 参数，当前调用只传了 `amount`。另外，
      当 `send_receipt` 抛异常时应记录日志并继续（不应回滚支付）。
    success_condition:
      test_passes: "test_payment_with_receipt"
      max_files_changed: 3

  # ... T03-T15 按 task-test-cases.md 填充 ...
  # 各任务的 task_description 直接来自 task-test-cases.md

# --- 对照组配置 ---
control:
  # 确保 control worker 不被 CEL 影响
  isolation:
    # control worker 的提示词中不含任何 CEL 触发词
    # 如果平台支持按 project 禁用 skill，在此声明
    disable_cel_skill: true   # codebuddy: 确保 skills/ 目录不包含 CEL
  prompt_template: |
    你是一个软件工程助手。请完成以下任务。

    ## 任务

    {task_description}

    ## 要求

    - 请完成上述任务。
    - 完成后请说明你做了什么。

    当前工作目录：{workspace_path}

# --- 实验组配置 ---
cel:
  # 确保 cel worker 加载 CEL 技能
  prompt_template: |
    请使用"收敛式工程迭代"技能完成以下任务。遵循技能的全部协议：
    每轮做最小更新、通过外部验证判断改进、误差下降则接受、上升则回滚。

    ## 任务

    {task_description}

    ## 要求

    - 加载并遵循 convergent-engineering-loop 技能的全部协议。
    - 使用对应参考文件定义误差度量。
    - 每轮输出迭代报告（含误差值、决策、下一步）。

    当前工作目录：{workspace_path}
  domain_prompt_overrides:
    代码开发: "逐步推进。每轮只做最小代码修改，通过运行测试验证改进。"
    测试工程: "分析测试失败并逐步修复。区分根因和症状，不要删除测试或削弱断言。"
    日志调试: "分析日志逐步定位根因。列出已知事实、活跃假设、排除假设，不要无证据猜测。"
    代码审查: "逐条处理 review comments。控制 PR 范围，不要加入无关修改。"
    文档编写: "只修正确实不同的部分，不要重写整篇文档。"
    Harness工程: "修复 CI 做到可复现、一键运行。固定依赖版本。"
    架构设计: "先设计方案、记录 ADR，确认方案后再实施。不要跳过设计直接写代码。"
    项目设计: "先收敛需求：梳理冲突、明确非目标、列出风险和验收标准。不要写代码。"
    交叉验证: "逐项核对计划标记是否与代码实际匹配，先评估再修正。"
    多域组合: "稳妥推进。按阻塞性维度优先处理。"
    震荡易发: "逐步推进，每轮只做最小更新。注意：不改变对外接口签名。"

# --- 指标采集配置 ---
metrics:
  collect:
    - test_results        # 最终测试通过/失败数
    - lint_results         # lint 错误数
    - type_check_results   # 类型检查错误数
    - git_diff_stat        # git diff --stat
    - rounds_count         # 对话轮次
    - token_count          # token 消耗（如平台 API 可获取）
    - wall_time            # 墙钟耗时

# --- 对比分析配置 ---
comparison:
  dimensions:
    - id: effectiveness
      weight: 0.30
      checks: [task_completed, all_checks_passed]
    - id: efficiency
      weight: 0.20
      checks: [rounds_count, token_count, wall_time]
    - id: stability
      weight: 0.25
      checks: [new_test_failures, unrelated_files_changed, edit_success_rate]
    - id: quality
      weight: 0.25
      checks: [final_test_pass_rate, lint_errors, min_modification_ratio]
```

---

## 三、主 Agent 编排协议

主 Agent 读取 `run_config.yaml` 后，按以下协议执行。

### 3.1 主 Agent 完整流程

```
─ 0. 初始化
│    ├── 读取 run_config.yaml
│    ├── 确定输出目录 test-runs/{platform}_{model}_{timestamp}
│    ├── 创建输出目录结构
│    └── 写入 manifest.yaml
│
─ 对 task_list 中的每个 task (T01 → T02 → ... → T15)：
│   │
│   ├── 1. 环境还原
│   │   ├── git checkout task/{task_id}-init
│   │   ├── git clean -fd
│   │   └── pip install -e . (if needed)
│   │
│   ├── 2. 对照组执行 (control)
│   │   ├── 构建 control prompt（基于 control.prompt_template）
│   │   ├── spawn control worker agent  ←  关键：新会话，隔离 CEL
│   │   ├── 等待 worker 完成（最多 max_rounds 轮）
│   │   ├── 采集 control 指标 → test-runs/.../T{id}/control/
│   │   └── 记录 control worker 对话日志
│   │
│   ├── 3. 环境还原（同步骤 1，重置到任务初始状态）
│   │
│   ├── 4. 实验组执行 (CEL)
│   │   ├── 构建 CEL prompt（基于 cel.prompt_template + domain 覆盖）
│   │   ├── spawn CEL worker agent  ←  关键：新会话，加载 CEL skill
│   │   ├── 等待 worker 完成（最多 max_rounds 轮）
│   │   ├── 采集 CEL 指标 → test-runs/.../T{id}/cel/
│   │   └── 记录 CEL worker 对话日志
│   │
│   ├── 5. 对比分析（当前 task）
│   │   ├── 读取 control/metrics.yaml 和 cel/metrics.yaml
│   │   ├── 计算各维度 Δ = CEL - Control
│   │   ├── 生成 task 级对比报告
│   │   └── 写入 test-runs/.../T{id}/comparison.yaml
│   │
│   └── 6. 检查是否继续
│       ├── 如果所有任务完成 → 进入步骤 7
│       └── 否则 → 下一个 task
│
─ 7. 聚合报告
│   ├── 汇总所有任务的 comparison.yaml
│   ├── 计算统计量（均值、p 值等）
│   └── 生成 report.md
```

### 3.2 Worker Agent 的隔离保证

| 条件 | Control Worker | CEL Worker |
|------|:---:|:---:|
| Prompt 含 CEL 触发词 | ❌ 严格不含 | ✅ 必须含 |
| CEL skill 已加载 | ❌ 确保不在 context | ✅ 已加载 |
| `.codebuddy/skills/` 目录 | 临时移除或确保不匹配 | 存在 |
| 对话轮次上限 | `max_rounds` | `max_rounds` |

**平台特定实现**：

#### CodeBuddy

```
# Control Worker: 使用不带 CEL 触发词的 prompt，确保 CEL skill 未被自动匹配
# CEL Worker:     使用带 CEL 触发词的 prompt
# 如果在同一项目中，Control Worker 可通过参数禁止加载特定 skill
```

#### Codex

```
# Control Worker: codex exec --no-skills -p "prompt"  (如果支持)
# CEL Worker:     codex exec -p "prompt"  (自动加载 .agents/skills/)
```

### 3.3 Worker Agent 的输入与输出

#### 输入

```yaml
# 主 Agent 给 Worker 的上下文
worker_context:
  task_id: "T01"
  group: "control"              # control | cel
  task_description: "..."       # 来自 run_config.yaml
  workspace_path: "/path/to/mock-project"
  max_rounds: 10
  git_head: "abc123"           # 用于 diff 基准
```

#### 期望输出

Worker 完成后，主 Agent 从 Worker 的完整输出中提取：

| 字段 | 来源 | 说明 |
|------|------|------|
| `completed` | Worker 最终声明 | 是否声称任务完成 |
| `rounds` | 对话消息计数 | 消耗了多少个 exchange |
| `agent_log` | 完整对话内容 | 用于后续人工审查 |
| `error_metric_final` | CEL Worker 专用 | 最终误差值（Control 无此字段） |
| `decision_history` | CEL Worker 专用 | 每轮的接受/回滚决策序列 |

#### 指标采集（主 Agent 执行命令）

Worker 完成后，主 Agent 自动运行以下命令采集客观指标：

```bash
# 测试结果
pytest --tb=short -q 2>&1 | tail -5

# Lint 结果
ruff check src/ --output-format=concise 2>&1 | wc -l

# 类型检查结果
mypy src/ --no-error-summary 2>&1 | wc -l

# Diff 统计
git diff --stat {git_head}

# 修改文件数
git diff --name-only {git_head} | wc -l

# 新增行 / 删除行
git diff --shortstat {git_head}
```

---

## 四、结果文件格式定义

### 4.1 `manifest.yaml` —— 运行元信息

```yaml
# test-runs/codex_claude-4.5_2026-07-21T143052Z/manifest.yaml
run_id: codex_claude-4.5_2026-07-21T143052Z
platform: codex
model: claude-4.5
started_at: 2026-07-21T14:30:52Z
finished_at: 2026-07-21T16:45:10Z    # 全部任务完成后填写
task_suite: T01-T15
total_tasks: 15
completed_tasks: 15
failed_tasks: 0
```

### 4.2 `session.yaml` —— 单次 Worker 会话

```yaml
# test-runs/.../T01/control/session.yaml
task_id: T01
group: control
worker_started_at: 2026-07-21T14:31:00Z
worker_finished_at: 2026-07-21T14:33:45Z
max_rounds: 10
actual_rounds: 4
completed: true           # Worker 声称完成
git_head_initial: abc123
git_head_final: def456
```

### 4.3 `metrics.yaml` —— 指标数据

```yaml
# test-runs/.../T01/control/metrics.yaml
task_id: T01
group: control

# === 效果 ===
effectiveness:
  task_completed: true              # 成功判定通过
  all_checks_passed: true           # 所有自动化检查通过
  requires_manual_intervention: false

# === 效率 ===
efficiency:
  rounds: 4
  total_tokens: 8450
  wall_time_seconds: 165
  effective_rounds: 3              # CEL 专用，Control 不填

# === 稳定性 ===
stability:
  files_changed: 1
  lines_added: 6
  lines_removed: 1
  new_test_failures: 0
  unrelated_files_changed: []       # 人工标注
  oscillation_detected: false
  edit_operations_total: 2         # Agent 发起的编辑操作次数
  edit_operations_failed: 0        # 失败的编辑操作次数

# === 质量 ===
quality:
  final_test_pass: 4               # 最终通过测试
  final_test_total: 4              # 总测试
  final_lint_errors: 0
  final_type_errors: 0
  min_modification_ratio: 1.2      # 实际修改行数 / 最少必要行数

# === 原始输出（采集用） ===
raw:
  test_command_output: "..."
  lint_command_output: "..."
  type_check_output: "..."
  git_diff_stat: " src/user_service.py | 6 +"
```

### 4.4 `comparison.yaml` —— 单任务对比

```yaml
# test-runs/.../T01/comparison.yaml
task_id: T01
domain: 代码开发

deltas:
  effectiveness:
    cel_completed: true
    control_completed: true
    same: true
  efficiency:
    cel_rounds: 3
    control_rounds: 4
    rounds_delta: -1            # CEL 少 1 轮
    cel_tokens: 7200
    control_tokens: 8450
    tokens_delta: -1250         # CEL 省 1250 token
    cel_wall_time: 142
    control_wall_time: 165
    time_delta: -23             # CEL 快 23 秒
  stability:
    cel_new_failures: 0
    control_new_failures: 0
    same: true
    cel_unrelated_files: 0
    control_unrelated_files: 0
    same: true
  quality:
    cel_test_pass_rate: 1.0
    control_test_pass_rate: 1.0
    same: true
    cel_modification_ratio: 1.0
    control_modification_ratio: 1.2

summary:
  cel_better_in: [efficiency.rounds, efficiency.tokens, quality.modification_ratio]
  control_better_in: []
  same_in: [effectiveness, stability, quality.test_pass_rate]
  winner: cel                   # cel | control | tie
```

### 4.5 `report.md` —— 最终聚合报告

```markdown
# CEL A/B 评价报告

- 运行 ID: codex_claude-4.5_2026-07-21T143052Z
- 平台: Codex
- 模型: Claude 4.5
- 任务范围: T01-T15
- 执行时间: 2026-07-21 14:30 - 16:45 (2h15m)

## 总体结果

| 维度 | 对照组 | 实验组(CEL) | CEL 优势 |
|------|:------:|:---------:|:--------:|
| 效果 (任务完成) | 12/15 | 13/15 | +1 |
| 效率 (平均轮次) | 6.2 | 4.8 | -22% 轮次 |
| 效率 (平均 Token) | 12.3k | 9.1k | -26% Token |
| 稳定性 (回归率) | 18% | 7% | -11pp |
| 稳定性 (范围漂移) | 22% | 5% | -17pp |
| 质量 (测试通过率) | 91% | 97% | +6pp |
| 质量 (修改精准度) | 2.8x | 1.3x | 更接近必要修改 |

## 按领域分

| 领域 | 任务 | CEL | Control | 胜者 |
|------|:----:|:---:|:-------:|:----:|
| 代码开发 | T01-T04 | — | — | CEL 3:1 |
| 测试工程 | T05-T06 | — | — | CEL 2:0 |
| 日志调试 | T07 | — | — | CEL |
| ... | ... | ... | ... | ... |

## 统计显著性

- Wilcoxon 符号秩检验（综合得分）：p = 0.023 (<0.05)
- 结论：CEL 组在综合得分上显著优于对照组

## 定性发现

- 对照组在 T04 中做了不必要格式化（范围漂移）
- 对照组在 T07 中跳过了假设验证直接改代码
- 对照组在 T15 中出现了 3 轮震荡
- 实验组在 T15 中通过最小更新逐轮降低误差，未发生震荡
```

---

## 五、主 Agent 启动提示词

主 Agent 自身可以使用以下提示词启动（或者用 `run_config.yaml` 直接作为 context 入口）：

```
你是一个测试编排 Agent。请读取 test-runs/run_config.yaml 中的配置，
按照 task_list 顺序串行执行所有任务的 A/B 测试。

## 你的职责

1. 读取 run_config.yaml
2. 在 test-runs/ 下创建本次运行的目录
3. 对 task_list 中的每个任务：
   a. 还原项目到任务初始状态
   b. 先 spawn 一个 control worker（完全隔离 CEL）完成任务
   c. 采集 control 结果
   d. 再还原项目
   e. 再 spawn 一个 cel worker（加载 CEL skill）完成同一任务
   f. 采集 cel 结果
   g. 对比两组结果，写入 comparison.yaml
4. 全部任务完成后，生成 report.md

## Worker 隔离规则

- Control Worker: 提示词不含任何 CEL 触发词
- CEL Worker: 提示词必须含"收敛式工程迭代"触发词，确保加载 skill
- 两个 Worker 使用独立的全新会话

## 指标采集规则

每个 Worker 完成后，在 mock 项目目录下执行以下命令采集指标：
- pytest --tb=short -q 2>&1
- ruff check src/ --output-format=concise 2>&1 | wc -l
- mypy src/ --no-error-summary 2>&1 | wc -l
- git diff --stat {初始 git_head}
- git diff --name-only {初始 git_head} | wc -l

## 输出

全部输出到 test-runs/{platform}_{model}_{timestamp}/ 目录下，
按上述目录结构组织。

现在开始执行。
```

---

## 六、与 `test-harness.md` 的关系

| 维度 | `test-harness.md`（脚本方案） | 本方案（Agent 编排） |
|------|-------------------------------|---------------------|
| 驱动方式 | Python 脚本直接调 CLI | 主 Agent 读取 config，spawn worker |
| Worker 会话 | 脚本控制 stdin/stdout | Agent 平台原生会话 |
| 适合场景 | 全自动化 CI、批量回归 | 交互式测试、人工观察 Agent 行为 |
| CEL 测试 | 通过脚本设置/取消 skill | 通过 prompt 中是否含触发词 |
| 结果采集 | 脚本捕获 stdout | 主 Agent 执行命令采集 |
| 可复现性 | 高（脚本确定性） | 中（Agent 行为有随机性） |

两者互补：脚本方案适合最终 CI 回归，Agent 编排方案适合开发和调试阶段的交互式验证。
