# CEL A/B 测试提示词

稳定的编排与审计协议已经封装在测试专用 skill 中。日常使用不需要复制长提示词。

## 推荐提示词

运行并审计默认主套件：

```text
使用 $cel-ab-evaluation 运行 primary 套件并审计结果。
```

指定平台和批次：

```text
使用 $cel-ab-evaluation，在 Codex 上运行 primary 套件并审计；
批次 ID 为 codex_gpt5_20260724T150000Z。
```

只运行、不做效果审计：

```text
使用 $cel-ab-evaluation 在 CodeBuddy 上运行 primary 套件。
```

审计已有批次：

```text
使用 $cel-ab-evaluation 审计批次：
G:\CodesG\codebuddy-code\ConvergentEngineerLoop\test-runs\<batch-id>
```

未指定批次 ID 时，skill 会按平台、模型和 UTC 时间生成唯一 ID。未指定 suite 时
默认使用 `primary`。

## 协议存放位置

- Skill 入口：`cel-eval-mock-project/skills/cel-ab-evaluation/SKILL.md`
- 批次运行协议：`cel-eval-mock-project/skills/cel-ab-evaluation/references/run.md`
- 结果审计协议：`cel-eval-mock-project/skills/cel-ab-evaluation/references/audit.md`
- 隔离设计：`meta_plan/experiment-isolation.md`
- 采集器说明：`cel-eval-mock-project/harness/README.md`

编排 Agent 触发 skill 后会按需读取运行或审计 reference；这些内容不需要进入每次
用户提示词。

## Worker 提示词

任务 worker 的提示词也不需要手工编写。创建批次后自动生成：

```text
<batch-root>/results/<task-id>/control/prompt.txt
<batch-root>/results/<task-id>/cel/prompt.txt
```

Control 与 CEL 共用任务正文，只有 CEL 组额外启用
`convergent-engineering-loop`。编排 Agent 必须直接使用生成文件，不得自行改写。

## 安装或同步

Skill 真源位于 `cel-eval-mock-project/skills/cel-ab-evaluation`。使用评测专用脚本
把它同步到当前仓库的 Codex 与 CodeBuddy 发现目录：

```powershell
python cel-eval-mock-project/sync_evaluation_skill.py

# 只校验副本是否与真源一致
python cel-eval-mock-project/sync_evaluation_skill.py --check
```

评测专用 skill 只同步到本仓库的 `.agents/skills/` 和 `.codebuddy/skills/`，不会
进入 CEL 产品文件夹包、插件包或常规项目安装。每个 CEL worker 所需的
`convergent-engineering-loop` 由 `_runner.py batch` 单独安装到对应 CEL 工作区；
Control 工作区不会安装。

不要在评测仓库根目录运行 `--install .`。脚本会主动拒绝这种操作，因为仓库级
treatment skill 可能被 Control worker 发现。

安装或更新编排 skill 后应启动一个新任务，让平台重新扫描项目 skills。
