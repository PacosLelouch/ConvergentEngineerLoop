# CEL A/B 评价 —— 测试 Harness 设计

> 自动化 A/B 测试的基础设施：环境准备、任务分发、结果采集、对比分析的脚本和流程设计。

---

## 一、整体流程

```
                    ┌──────────────────────────┐
                    │  1. 环境准备              │
                    │  - checkout task init     │
                    │  - install deps           │
                    │  - 记录初始指标快照        │
                    └──────────┬───────────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
    ┌──────────▼──────────┐      ┌─────────────▼──────────┐
    │ 2a. 对照组执行       │      │ 2b. 实验组执行          │
    │ - 加载 Control 提示词 │      │ - 加载 CEL 提示词       │
    │ - Agent 自由执行      │      │ - Agent CEL 协议执行    │
    │ - 采集过程数据        │      │ - 采集过程数据          │
    └──────────┬──────────┘      └─────────────┬──────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  3. 结果采集          │
                    │  - git diff 统计      │
                    │  - 测试结果           │
                    │  - lint/type 结果     │
                    │  - 轮次/token/耗时    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  4. 对比分析          │
                    │  - 指标计算           │
                    │  - 统计检验           │
                    │  - 生成报告           │
                    └──────────────────────┘
```

---

## 二、脚本设计

### 2.1 目录结构

```
test-harness/
├── run_experiment.py       # 主脚本：编排一次完整 A/B 实验
├── setup_env.py            # 环境准备：checkout + install + 初始快照
├── collect_metrics.py      # 结果采集：从执行产物中提取指标
├── analyze_results.py      # 对比分析：计算指标差异、统计检验、生成报告
├── config.yaml             # 实验配置
├── prompts/
│   ├── control_template.txt    # 对照组提示词模板
│   └── cel_template.txt       # 实验组提示词模板
├── task_configs/
│   ├── T01.yaml            # 每个任务的配置
│   ├── T02.yaml
│   └── ...
├── results/                # 结果输出目录
│   ├── T01/
│   │   ├── control/
│   │   │   ├── agent_log.txt       # Agent 完整对话日志
│   │   │   ├── metrics.json        # 采集的指标
│   │   │   └── git_diff.patch      # git diff
│   │   └── cel/
│   │       ├── agent_log.txt
│   │       ├── metrics.json
│   │       └── git_diff.patch
│   └── ...
└── report/                 # 最终报告输出
    └── ab_report.md
```

### 2.2 实验配置 `config.yaml`

```yaml
# 全局配置
mock_project_path: "../cel-eval-mock-project"
agent_platform: "codebuddy"      # codebuddy | claude | codex
agent_model: "claude-4.5"        # 固定模型版本，保证可比性
max_rounds_simple: 10
max_rounds_medium: 20
max_rounds_complex: 35

# 要运行的任务列表
tasks:
  - id: T01
    config: task_configs/T01.yaml
    enabled: true
  - id: T02
    config: task_configs/T02.yaml
    enabled: true
  # ... 全部 15 个任务

# 指标权重（用于综合评分）
metric_weights:
  effectiveness: 0.30
  efficiency: 0.20
  stability: 0.25
  quality: 0.25
```

### 2.3 任务配置示例 `task_configs/T01.yaml`

```yaml
id: T01
domain: 代码开发
complexity: simple
init_branch: task/T01-init
expected_branch: task/T01-expected

# 任务描述（占位符将被填充到提示词模板中）
task_description: |
  `src/user_service.py` 中 `get_user_by_id` 函数在传入不存在的 user_id 时抛出 `NoneTypeError`（第 42 行访问 `user.name`），请修复它。

# 成功判定条件（自动化检查）
success_checks:
  - type: test_pass
    command: "pytest tests/test_user_service.py -v"
    expected: all_pass
  - type: git_diff_files_max
    max_files: 2              # 最多修改 2 个文件
  - type: git_diff_file_pattern
    pattern: "src/user_service.py"  # 必须在此文件

# 初始指标采集命令
initial_metrics:
  test_command: "pytest --tb=short 2>&1"
  lint_command: "ruff check src/ 2>&1 | wc -l"
  type_check_command: "mypy src/ --no-error-summary 2>&1 | wc -l"
```

### 2.4 `run_experiment.py` 伪代码

```python
"""
主实验编排脚本。

用法：
    python run_experiment.py --task T01       # 运行单个任务的 A/B 实验
    python run_experiment.py --all            # 运行所有任务
    python run_experiment.py --task T01 --group control  # 只跑对照组
    python run_experiment.py --task T01 --group cel      # 只跑实验组
"""

import yaml, subprocess, json, shutil, os, time, argparse
from pathlib import Path
from datetime import datetime


def setup_environment(task_config, mock_project_path, group):
    """步骤 1 + 2a/2b 前：还原任务初始状态，记录初始快照"""
    project = Path(mock_project_path)
    init_branch = task_config['init_branch']

    # git checkout 到初始状态
    subprocess.run(['git', 'checkout', init_branch], cwd=project, check=True)
    subprocess.run(['git', 'clean', '-fd'], cwd=project, check=True)
    subprocess.run(['pip', 'install', '-e', '.'], cwd=project, check=True)

    # 记录初始快照
    initial = collect_initial_snapshot(project, task_config)
    return initial


def collect_initial_snapshot(project, task_config):
    """采集任务初始状态的指标基线"""
    snapshot = {}
    for key, cmd in task_config.get('initial_metrics', {}).items():
        result = subprocess.run(cmd, shell=True, cwd=project,
                                capture_output=True, text=True)
        snapshot[key] = result.stdout
    # git HEAD hash
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=project,
                            capture_output=True, text=True)
    snapshot['git_head'] = result.stdout.strip()
    return snapshot


def run_agent_session(task_config, group, mock_project_path, config):
    """
    启动 Agent 会话执行任务。

    这是一个异步/长时间步骤，具体实现依赖于平台：
    - CodeBuddy: 通过 CodeBuddy API 或 CLI 启动会话
    - Claude Code: 通过 Claude Code CLI 启动会话
    - Codex: 通过 Codex CLI 启动会话

    返回: session_result = {
        'agent_log': str,        # 完整对话日志
        'rounds': int,           # 对话轮次
        'total_tokens': int,     # 总 token
        'wall_time': float,      # 耗时（秒）
        'completed': bool,       # Agent 是否声明完成
        'agent_declared_done': bool,
    }
    """
    prompt_template = load_prompt_template(group)
    task_prompt = fill_prompt(prompt_template, task_config)

    # 将 prompt 发送给 Agent 平台，采集会话数据
    # 具体实现见 2.6 各平台适配
    ...


def collect_results(project, task_config, initial, session_result):
    """步骤 3：从执行产物中采集指标"""
    metrics = {}

    # git diff 统计
    diff_result = subprocess.run(
        ['git', 'diff', '--stat', initial['git_head']],
        cwd=project, capture_output=True, text=True)
    metrics['diff_stat'] = diff_result.stdout
    metrics['files_changed'] = count_changed_files(diff_result.stdout)
    metrics['lines_added'] = count_added_lines(diff_result.stdout)
    metrics['lines_removed'] = count_removed_lines(diff_result.stdout)

    # 解析 diff 统计
    diff_detail = subprocess.run(
        ['git', 'diff', initial['git_head']],
        cwd=project, capture_output=True, text=True)
    metrics['diff_patch'] = diff_detail.stdout

    # 测试结果
    if 'test_command' in task_config.get('initial_metrics', {}):
        test_result = subprocess.run(
            task_config['initial_metrics']['test_command'],
            shell=True, cwd=project, capture_output=True, text=True)
        metrics['final_test_output'] = test_result.stdout
        metrics['final_test_pass_count'] = count_passed(test_result.stdout)
        metrics['final_test_fail_count'] = count_failed(test_result.stdout)

    # lint 结果
    if 'lint_command' in task_config.get('initial_metrics', {}):
        lint_result = subprocess.run(
            task_config['initial_metrics']['lint_command'],
            shell=True, cwd=project, capture_output=True, text=True)
        try:
            metrics['final_lint_errors'] = int(lint_result.stdout.strip())
        except ValueError:
            metrics['final_lint_errors'] = -1  # 解析失败

    # 合并会话数据
    metrics.update(session_result)
    return metrics


def check_success(task_config, metrics):
    """检查任务是否成功完成"""
    for check in task_config['success_checks']:
        if check['type'] == 'test_pass':
            if check['expected'] == 'all_pass':
                if metrics.get('final_test_fail_count', 999) > 0:
                    return False, f"Tests still failing"
        elif check['type'] == 'git_diff_files_max':
            if metrics.get('files_changed', 999) > check['max_files']:
                return False, f"Too many files changed"
    return True, "All checks passed"


def run_single_task(task_config, config, group=None):
    """执行单个任务的一次实验（对照组或实验组）"""
    groups_to_run = [group] if group else ['control', 'cel']
    mock_project = config['mock_project_path']

    for grp in groups_to_run:
        print(f"  [{grp}] 开始...")

        # 1. 还原环境
        initial = setup_environment(task_config, mock_project, grp)

        # 2. 运行 Agent 会话
        start_time = time.time()
        session_result = run_agent_session(task_config, grp, mock_project, config)
        session_result['wall_time'] = time.time() - start_time

        # 3. 采集结果
        metrics = collect_results(mock_project, task_config, initial, session_result)

        # 4. 判定成功
        success, reason = check_success(task_config, metrics)
        metrics['success'] = success
        metrics['success_reason'] = reason

        # 5. 保存
        output_dir = Path(config.get('results_dir', 'results')) / task_config['id'] / grp
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / 'metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        with open(output_dir / 'agent_log.txt', 'w', encoding='utf-8') as f:
            f.write(session_result.get('agent_log', ''))
        with open(output_dir / 'git_diff.patch', 'w') as f:
            f.write(metrics.get('diff_patch', ''))

        print(f"  [{grp}] 完成 (success={success})")

    return True


def run_all_tasks(config, group=None):
    """运行全部任务"""
    for task_entry in config['tasks']:
        if not task_entry.get('enabled', True):
            continue
        task_config = load_task_config(task_entry['config'])
        print(f"\n{'='*60}")
        print(f"任务 {task_config['id']}: {task_config['domain']}")
        print(f"{'='*60}")
        run_single_task(task_config, config, group)
```

### 2.5 `collect_metrics.py` 指标提取详情

从 Agent 会话日志和 git 状态中提取以下指标：

```python
# metrics.json 结构
{
    # === 效果维度 ===
    "success": true,                    # 是否成功完成
    "manual_intervention": false,       # 是否需人工介入
    "checks_passed": 3,                 # 通过的自动化检查数
    "checks_total": 3,                  # 总自动化检查数

    # === 效率维度 ===
    "rounds": 5,                        # 对话轮次
    "total_tokens": 12450,              # 总 token
    "input_tokens": 9800,               # 输入 token
    "output_tokens": 2650,              # 输出 token
    "wall_time_seconds": 182.5,         # 耗时
    "effective_rounds": 4,             # 有效改进轮次（误差下降的轮次）
    "total_rounds": 5,                 # 总轮次

    # === 稳定性维度 ===
    "files_changed": 1,                 # 修改文件数
    "lines_added": 6,                   # 新增行数
    "lines_removed": 1,                 # 删除行数
    "new_test_failures": 0,            # 新增测试失败
    "oscillation_count": 0,             # 震荡次数
    "same_file_reversions": 0,          # 同一文件来回修改次数
    "file_consecutive_edits_max": 2,   # 同一文件最多连续编辑轮次
    "unrelated_files_changed": [],      # 修改的无关文件列表（需人工标注）
    "edit_success_rate": 1.0,          # 编辑操作成功率

    # === 质量维度 ===
    "final_test_pass_count": 4,        # 最终通过测试数
    "final_test_fail_count": 0,        # 最终失败测试数
    "final_lint_errors": 0,            # 最终 lint 错误数
    "final_type_errors": 0,            # 最终类型错误数
    "min_modification_ratio": 1.2,     # 实际修改行数 / 最少必要修改行数
    "diff_explainability": null,       # diff 可解释性（人工评分，先不填）
    "decision_traceability": null,     # 决策可追溯性（人工评分，先不填）

    # === 原始数据 ===
    "diff_stat": "...",                # git diff --stat 输出
    "diff_patch": "...",               # git diff 完整 patch
    "final_test_output": "...",        # 最终测试输出
    "git_head_initial": "abc123",        # 初始 commit
    "git_head_final": "def456",          # 最终 commit
}
```

### 2.6 各平台 Agent 会话采集适配

```python
# ============================================================
# 平台适配层
# 不同平台的 Agent 调用方式不同，此处定义统一接口
# ============================================================

def load_prompt_template(group):
    """加载对应组的提示词模板"""
    if group == 'control':
        path = 'prompts/control_template.txt'
    else:
        path = 'prompts/cel_template.txt'
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def fill_prompt(template, task_config):
    """填充任务描述到提示词模板"""
    return template.replace('{task_description}', task_config['task_description'])


# --- CodeBuddy 适配 ---

def run_codebuddy_session(filled_prompt, workspace_path, max_rounds):
    """
    通过 CodeBuddy API 启动会话。

    CodeBuddy 会话管理（假想 API）：
    - POST /api/sessions 创建会话
    - POST /api/sessions/{id}/messages 发送消息
    - GET  /api/sessions/{id} 获取会话状态
    """
    # 使用 CodeBuddy MCP 或 CLI 启动会话
    # 具体实现取决于 CodeBuddy 提供的 API
    # 这里作为示例提供伪代码
    pass


# --- Claude Code 适配 ---

def run_claude_code_session(filled_prompt, workspace_path, max_rounds):
    """
    通过 Claude Code CLI 启动会话。

    claude --print --max-turns {max_rounds} -p "{prompt}"
    """
    cmd = [
        'claude',
        '--print',
        f'--max-turns={max_rounds}',
        '-p', filled_prompt
    ]
    result = subprocess.run(
        cmd, cwd=workspace_path,
        capture_output=True, text=True, timeout=600
    )
    # 解析 Claude Code 输出
    return parse_claude_output(result)


# --- Codex 适配 ---

def run_codex_session(filled_prompt, workspace_path, max_rounds):
    """
    通过 Codex CLI 启动会话。

    codex exec --max-turns {max_rounds} "{prompt}"
    """
    cmd = [
        'codex', 'exec',
        f'--max-turns={max_rounds}',
        filled_prompt
    ]
    result = subprocess.run(
        cmd, cwd=workspace_path,
        capture_output=True, text=True, timeout=600
    )
    return parse_codex_output(result)
```

### 2.6 `analyze_results.py` 设计

```python
"""
对比分析脚本。

读取 results/ 目录下所有任务的 metrics.json，计算：
- 每任务的 Δ 值（CEL - Control）
- 各维度的聚合统计
- 统计显著性检验
- 生成 Markdown 报告
"""

import json, statistics, math
from pathlib import Path
from collections import defaultdict


def load_all_results(results_dir):
    """加载所有任务的结果"""
    ...


def compute_metric_deltas(task_results):
    """计算每个任务的各指标 Δ = cel - control"""
    ...


def compute_dimension_scores(metrics, weights_config):
    """
    将 16 个指标聚合为 4 个维度得分（归一化到 [0,1]）。

    effectivenss: EFF-1 (完成率) + EFF-2 (需求满足度) + EFF-3 (首次成功率)
    efficiency:   EFC-1 (平均轮次, 反向) + EFC-2 (token消耗, 反向) + EFC-3 (耗时, 反向) + EFC-4 (轮次有效率)
    stability:    STB-1 (回归率, 反向) + STB-2 (震荡率, 反向) + STB-3 (漂移率, 反向) + STB-4 (编辑成功率)
    quality:      QLT-1 (测试通过率) + QLT-2 (lint清洁度, 反向) + QLT-3 (最小修改度, 反向) + QLT-4 (diff可解释性) + QLT-5 (决策可追溯性)
    """
    ...


def paired_test(control_scores, cel_scores):
    """
    Wilcoxon 符号秩检验（配对非参数检验）。

    返回: (statistic, p_value)
    """
    ...


def generate_report(all_deltas, stats_result, weights_config):
    """生成 Markdown 格式的 A/B 对比报告"""
    report = f"""# CEL A/B 评价报告

生成时间：{datetime.now().isoformat()}

## 总体结果

| 维度 | 对照组均值 | 实验组均值 | Δ | Δ% | 显著性 |
|------|:---------:|:---------:|:---:|:---:|:------:|
| 效果 (Effectiveness) | ... | ... | ... | ... | ... |
| 效率 (Efficiency) | ... | ... | ... | ... | ... |
| 稳定性 (Stability) | ... | ... | ... | ... | ... |
| 质量 (Quality) | ... | ... | ... | ... | ... |
| **综合** | ... | ... | ... | ... | ... |

## 按领域分

...
"""
    return report
```

---

## 三、手动评分指南

以下指标无法完全自动化，需人工评分（存储到 metrics.json 的对应字段）。

### 3.1 需求满足度（EFF-2）

| 分数 | 标准 |
|:----:|------|
| 5 | 完全满足任务描述的所有要求，无遗漏 |
| 4 | 满足主要要求，有 1 个小的边缘情况未处理 |
| 3 | 满足大部分要求，有 1-2 个遗漏 |
| 2 | 只满足部分要求，关键要求未完成 |
| 1 | 几乎未满足任务要求 |

### 3.2 diff 可解释性（QLT-4）

| 分数 | 标准 |
|:----:|------|
| 5 | 每个 diff 块都与任务直接相关，无无关修改 |
| 4 | 绝大部分 diff 与任务相关，有 1-2 行多余格式化 |
| 3 | diff 基本与任务相关，但有少量不必要重构 |
| 2 | diff 中有明显不相关的修改（改了无关文件/函数） |
| 1 | 大量无关修改，diff 远超任务范围 |

### 3.3 决策可追溯性（QLT-5）

仅适用于实验组（CEL 组）。对照组跳过。

| 分数 | 标准 |
|:----:|------|
| 5 | 每轮都有清晰的误差度量、决策理由、下一步 |
| 4 | 大部分轮次有度量与决策，少数缺失 |
| 3 | 部分轮次有输出但不够完整 |
| 2 | 输出混乱，难以追溯决策链 |
| 1 | 无结构化输出，完全不可追溯 |

### 3.4 无关文件标注（STB-3 计算用）

人工审查 diff 中每个修改的文件，标注是否为"任务描述外"的无关文件。存入 `metrics.json` 的 `unrelated_files_changed` 字段。

---

## 四、实验执行计划

### 4.1 准备阶段

1. 创建 `cel-eval-mock-project` 仓库，为每个 task 建立 init 和 expected branch
2. 在目标平台上安装 CEL skill（实验组专用）
3. 验证 mock 项目在每个 task init branch 上可正常运行（初始测试有预期失败）
4. 验证 mock 项目在每个 task expected branch 上全部测试通过

### 4.2 执行阶段

建议执行顺序：
1. **先跑 3 个典型任务** (T01, T07, T14) 作为 Pilot，验证整个流程可行
2. Pilot 通过后跑全部 15 个任务
3. 如有时间，重复执行 2-3 轮以增强统计显著性

### 4.3 注意事项

- **同一任务的两个组应在相近时间执行**（同一小时内），减少 Agent 模型行为漂移的影响
- **每任务执行前必须 git clean + reset**，确保环境干净
- **记录 Agent 模型版本**（如 claude-4.5-20250701），如果后续模型更新，可能需要重跑实验
- **如果 Agent 请求用户输入**，对照组和实验组都应回复相同内容（如"请继续"或"你自己决定"），不提供额外指导
