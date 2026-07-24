# CEL A/B 实验隔离设计

本文是当前可执行流程的隔离规范。旧文档中复用 `working/`、让 worker 写
`agent_log.txt`、或直接在 agent 工作区运行外部审计测试的步骤均已废弃。

可直接交给编排 Agent 和审计 Agent 的提示词见
`cel-eval-mock-project/README.md`。

## 结论

在 worker 只拥有当前任务工作区写权限的正常实验模型下，流程满足以下三项要求：

1. Control 与 CEL 没有共享的可变任务状态；
2. 审计机制不向模型提供额外反馈，也不在 agent 工作区运行验证；
3. 不同批次不复用目录，CEL 真源和评测真源在运行前后接受摘要校验。

如果“完全隔离”指能够抵御恶意 worker 主动访问宿主机其他路径，则还需要容器、
虚拟机或独立操作系统账户。单纯的目录分离不能替代操作系统安全边界。

## 目录边界

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
        └── cel/
```

隔离单位是 `批次 × 任务 × 分组`。`_runner.py batch` 遇到已存在的批次目录会
直接失败，不会覆盖、清空或追加历史产物。

每个任务的两个工作区都从相同的 `base + task overlay` 独立复制。创建批次时会
计算忽略运行时技能目录后的任务载荷摘要，摘要不相同则拒绝创建。

每个工作区初始化为独立 Git 仓库，因此 Codex 的仓库级 skill 扫描在该工作区
停止；runner 同时把 worker 的 HOME/USERPROFILE 指向工作区内的空隔离目录，
避免加载用户级 CEL skill。批次创建前还会拒绝父目录中的 treatment skill。

## 唯一实验处理

两组共享的提示词只包括任务描述、工作目录、最小范围和正常验证要求。

- Control：只接收公共提示词，不加入“禁止 CEL”“不要迭代”等负向约束；
- CEL：在公共提示词后增加加载 CEL 技能的指令，并安装一次性技能副本。

因此组间有意差异只有 CEL 处理本身。平台、模型、最大轮次、权限策略和观察 hook
必须保持一致。

CEL 技能真源位于 `_shared/skills/convergent-engineering-loop`。worker 使用的
是批次 CEL 工作区内的一次性安装副本，不会直接修改真源。Control 工作区不安装
该副本。

A/B 评测编排 skill 真源位于
`cel-eval-mock-project/skills/cel-ab-evaluation`，只同步到当前评测仓库的
`.agents/skills/` 与 `.codebuddy/skills/` 供主编排 Agent 发现。产品文件夹包、
插件包和常规项目安装均不包含该 skill；它也不会被安装进任何 worker 工作区。

## 观察器非干预

`PostToolUse` hook 只比较工作区内容摘要。没有内容变化的只读工具不会产生伪轮次。

发生变化后，采集器执行以下步骤：

1. 复制当前任务状态到结果目录下的一次性验证镜像；
2. 在镜像中运行 pytest、Ruff 和任务验收；
3. 只把日志和结构化结果写入该组结果目录；
4. 删除验证镜像；
5. hook 返回空结果，不把误差值或验证输出放入模型上下文。

这避免了测试缓存、临时文件以及测试自身写文件污染 agent 工作区。同步 hook 会
增加运行时间，但两组使用同一机制，因此它是对称的测量开销，不构成 CEL 专属
反馈。耗时指标应区分 agent API 时间与包含审计开销的墙钟时间。

## 真源完整性

创建批次时记录以下内容的稳定摘要：

- CEL 执行技能与 A/B 评测技能真源；
- harness 与任务验收器；
- 正确基线与任务 overlay；
- 活动任务清单与运行器。

平台适配器在每次运行前后检查摘要。`verify_batch` 会再次检查，并验证 CEL
一次性安装副本未在运行中改变。任一检查失败，该运行不能进入 A/B 聚合。

## 同一编排 Agent 的执行约束

同一个编排 Agent 可以顺序启动全部任务，但每次只能把对应
`results/<task>/<group>/collector-config.json` 和 `prompt.txt` 交给 worker。
不能复用 worker 会话、工作区、平台 session ID 或结果目录。

推荐固定顺序时使用交替或随机化的组顺序，避免长期上下文、热缓存和时间趋势总是
偏向同一组。若平台无法创建无历史的新 worker session，则不能声称两组具有模型
上下文隔离。

## 验收命令

```powershell
python _runner.py batch <batch-id> codex primary
python _runner.py verify_batch ../test-runs/<batch-id>
```

只有 `isolation-report.json` 中 `ok=true`、所有初始任务载荷相等且所有真源摘要
一致的批次，才允许进入统计分析。
