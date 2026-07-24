# CEL A/B 评测运行指南

这里是 CEL 与 Control 隔离 A/B 实验的用户入口。实验设计和论证放在
`meta_plan/`，可执行流程、任务、采集器和运行说明统一放在本目录。

## 使用 Agent 运行（推荐）

在仓库根目录启动一个新的 Codex 或 CodeBuddy Agent 任务，输入：

```text
使用 $cel-ab-evaluation 运行 primary 套件并审计结果。
```

指定平台和批次 ID：

```text
使用 $cel-ab-evaluation，在 Codex 上运行 primary 套件并审计结果；
批次 ID 为 codex_gpt5_20260724T150000Z。
```

未指定 suite 时默认使用 `primary`；未指定批次 ID 时，skill 会按平台、模型和
UTC 时间生成唯一 ID。完整编排步骤已经封装在评测 skill 中，不要复制或手工改写
worker 提示词。

只运行、不做效果审计：

```text
使用 $cel-ab-evaluation 在 CodeBuddy 上运行 primary 套件。
```

审计已有批次：

```text
使用 $cel-ab-evaluation 审计批次：
G:\CodesG\codebuddy-code\ConvergentEngineerLoop\test-runs\<batch-id>
```

## 手工运行

在 `cel-eval-mock-project` 目录创建不可复用的新批次：

```powershell
python _runner.py batch <batch-id> <codex或codebuddy> primary
```

然后读取新批次的 `batch-manifest.json`。对清单中的每个 `任务 × 分组`，直接使用
清单给出的 config 和 prompt，并为每次调用启动全新 worker session：

```powershell
# Codex
python -m harness.codex_runner --config <config> --prompt-file <prompt>

# CodeBuddy
node harness/codebuddy_runner.mjs --config <config> --prompt-file <prompt>
```

全部运行结束后：

```powershell
python _runner.py verify_batch <batch-root>
python generate_comparison.py <batch-root>\results
```

禁止复用已有批次或结果目录；重试必须换新的 batch ID。Control 与 CEL 必须使用
相同模型、权限策略和预算。

## 产物位置

批次创建后，配置和提示词位于：

```text
<batch-root>/results/<task-id>/control/
├── collector-config.json
└── prompt.txt

<batch-root>/results/<task-id>/cel/
├── collector-config.json
└── prompt.txt
```

运行结果、checkpoint、指标、隔离报告和 comparison 均写入该批次目录，不修改
CEL 真源、评测 harness、base、tasks 或任务清单。

## 协议与实现文档

- Agent 入口：`skills/cel-ab-evaluation/SKILL.md`
- 批次运行协议：`skills/cel-ab-evaluation/references/run.md`
- 结果审计协议：`skills/cel-ab-evaluation/references/audit.md`
- 采集器与平台命令：`harness/README.md`
- 隔离设计：`../meta_plan/experiment-isolation.md`
- 活动任务清单：`task_suite.json`

## 同步评测 skill

在仓库根目录执行：

```powershell
python cel-eval-mock-project/sync_evaluation_skill.py

# 只检查真源与平台发现副本是否一致
python cel-eval-mock-project/sync_evaluation_skill.py --check
```

该脚本只把评测 skill 同步到当前仓库的 `.agents/skills/` 和
`.codebuddy/skills/`。它不会进入 CEL 产品文件夹包、插件包、常规项目安装或
任何 worker 工作区。
