# CEL 过程指标采集器

采集器在平台工具真正改变任务工作区后记录 checkpoint，并在一次性验证镜像中
运行 pytest、Ruff 和任务专用验收。验证进程不会在 agent 工作区内创建缓存、
临时文件或其他可观察状态。

需要交给主编排 Agent 或独立审计 Agent 的可复制提示词，见
`meta_plan/test-run-prompts.md`。

## 推荐流程

先创建一个不可复用的新批次：

```powershell
python _runner.py batch codex_gpt5_20260724T120000Z codex primary
```

该命令一次性生成：

```text
test-runs/<batch-id>/
├── source-guard.json
├── batch-manifest.json
├── workspaces/
│   └── <task-id>/
│       ├── control/
│       └── cel/
└── results/
    └── <task-id>/
        ├── control/
        │   ├── collector-config.json
        │   └── prompt.txt
        └── cel/
            ├── collector-config.json
            └── prompt.txt
```

Control 与 CEL 是从同一份 `base + task overlay` 分别复制得到的。任务载荷摘要
必须完全相同。CEL 工作区会额外安装一次性的 CEL 技能副本；Control 工作区没有
该副本。每个工作区还会初始化为独立 Git 仓库并使用空的隔离用户目录，以截断
父仓库和用户级 skill 发现。技能真源不会复制回写，也不会交给 worker 修改。

## 运行 Codex

```powershell
python -m harness.codex_runner `
  --config <批次目录>/results/T02/control/collector-config.json `
  --prompt-file <批次目录>/results/T02/control/prompt.txt
```

CEL 组使用同一任务下 `cel` 目录中的配置和提示词。适配器运行
`codex exec --json`，并通过同步 `PostToolUse` hook 检测工作区内容变化。

## 运行 CodeBuddy

先安装 `@tencent-ai/agent-sdk`，然后执行：

```powershell
node harness/codebuddy_runner.mjs `
  --config <批次目录>/results/T02/control/collector-config.json `
  --prompt-file <批次目录>/results/T02/control/prompt.txt
```

CodeBuddy 适配器使用同样的同步 `PostToolUse` 采集逻辑。两组必须保持相同模型、
权限模式、最大轮次和平台配置。

## 隔离保证

- 已存在的批次目录会被拒绝，历史结果不会被覆盖或追加。
- 每个 `批次 × 任务 × 分组` 都有独立工作区和独立结果目录。
- 结果目录与工作区互不包含。
- 外部验证在结果目录下的一次性镜像中执行，完成后删除镜像。
- hook 成功时不向模型返回验证结果；Control 与 CEL 使用同一观察器。
- Control 使用中性公共提示词，不包含“不要遵循 CEL”等额外行为约束。
- CEL 真源、harness、任务模板和验收器均受摘要守卫保护。

批次完成后执行：

```powershell
python _runner.py verify_batch <批次目录>
```

输出 `isolation-report.json`。任何真源变化、CEL 运行副本变化或路径越界都会使
验证失败。

## 产物

每次运行会在独立结果目录中生成原始平台事件、标准化事件、checkpoint 验证日志、
`checkpoints.jsonl`、`run.json` 和归约后的 `metrics.json`。Agent 自己编写的
日志不作为数值指标来源。

## 边界说明

上述机制保证实验状态和产物的逻辑隔离，并能检测真源污染。它不是针对恶意进程的
操作系统安全边界：如果 worker 被授予任意宿主机路径的写权限，目录约定本身无法
阻止其主动越界。正式实验仍应让平台只授予当前任务工作区写权限；需要对抗恶意
worker 时，应再使用容器、虚拟机或独立操作系统账户。
