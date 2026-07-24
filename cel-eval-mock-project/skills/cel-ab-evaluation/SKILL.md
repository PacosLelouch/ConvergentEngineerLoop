---
name: cel-ab-evaluation
description: 在本仓库运行或审计相互隔离的 CEL 与 Control A/B 实验。当用户要求运行 CEL primary 任务套件、创建评测批次、比较有无 CEL 的 worker、验证实验隔离、审计已有批次或汇总 CEL 客观评测指标时使用。
---

# CEL A/B 评测

把用户的短指令转换为确定性的批次运行或审计流程。不要要求用户复制完整编排协议。

## 选择模式

- 用户要求运行、测试或比较：读取 `references/run.md` 并执行。
- 用户要求审计已有批次：读取 `references/audit.md` 并执行。
- 用户要求“运行并审计”：先读取并执行 `references/run.md`，完成后再读取并执行
  `references/audit.md`。

## 默认值

- 从包含 `cel-eval-mock-project` 和 `meta_plan` 的目录确定仓库根目录。
- 默认套件为 `primary`。
- 用户未指定平台时，从当前 Agent 平台推断；不能可靠推断时只询问平台。
- 用户未指定批次 ID 时，生成
  `<platform>_<model-or-default>_<UTC timestamp>`，不得复用已有目录。

## 不变量

- 同一个主 Agent 可以编排全部运行，但每个 `任务 × 分组` 必须使用全新 worker
  session、独立工作区和独立结果目录。
- 只使用 `_runner.py batch` 生成的 config 和 prompt，不自行改写 worker 提示词。
- Control 不加入“禁止 CEL”或“不要迭代”等负向干预。
- 不修改 CEL 真源、harness、base、tasks、task suite 或已有批次。
- 不把一组结果反馈给另一组；不使用 agent 自报数字补齐客观指标。
- 任何隔离或完整性检查失败时停止效果结论，并报告失败原因。

## 交付

简短报告批次路径、完成/失败运行、隔离状态、comparison 和审计报告位置。只有用户
要求时才展开逐项指标。
