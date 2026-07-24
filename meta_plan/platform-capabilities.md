# Codex vs CodeBuddy 指标采集能力矩阵

调研时间：2026-07-22；实现校验：2026-07-24

> 实现结论：5 项核心指标均可采集，但 checkpoint 必须定义为“成功工具调用后，工作区内容指纹确实变化”，不能把平台的 assistant message 或 `turn.completed` 直接等同于工程迭代轮次。实现位于 `cel-eval-mock-project/harness/`。

---

## 一、Codex（`codex exec --json`）

### 数据源

```bash
codex exec --json --model gpt-5.6-luna-medium -C {workspace} "{prompt}"
```

JSONL 输出流中的关键事件类型：

| 事件 | 包含字段 |
|------|---------|
| `turn.started` | 顶层 turn 开始；单次 `exec` 通常只有一个，不能当修改轮次 |
| `turn.completed` | `usage: {input_tokens, cached_input_tokens, output_tokens}` |
| `item.completed` + `file_change` | `item.changes[].path`（不是 `item.path`） |
| `item.completed` + `command_execution` | `item.command`, `item.aggregated_output`, `item.exit_code` |
| `PostToolUse` hook | 工具完成后同步触发；结合工作区内容指纹确定 mutation checkpoint |

### 5 项指标能力

| 指标 | 可采集 | 采集方式 |
|------|:---:|------|
| **CNV-4 Token 消耗** | ✅ | `turn.completed.usage.input_tokens + output_tokens`，按 turn 累加；也可取总 input_tokens（含 cache） |
| **CNV-2 收敛稳定性** | ✅ | 同步 `PostToolUse` 后比较内容指纹；仅变化时运行 pytest/目标文件 ruff/任务验收，记录误差序列 |
| **CNV-3 轮次有效率** | ✅ | 统计误差下降的轮次数 / 总轮次数（基于 CNV-2 的误差序列） |
| **OSC-1 震荡位置** | ✅ | checkpoint 中记录实际变化文件及哈希，检测修改 ≥3 次或内容 A→B→A |
| **EXP-1 范围漂移** | ✅ | 实际变化路径与任务显式 `allowed_paths` 对比；不依赖工具参数猜测 |
| **OSC-2 震荡严重度** | ✅ | 震荡文件的平均修改次数 |
| **DEC-2 验证步骤数** | ✅ | 统计观察器实际执行并落盘的 validation 记录；平台命令事件用于交叉审计 |

### 中间快照注入方案

```python
# PostToolUse 同步 hook 伪代码
current = manifest(workspace)
if current != previous:
    changed_paths = diff(previous, current)
    validation_copy = disposable_copy(workspace, outside=workspace)
    pytest_result = run_fixed_argv(pytest_argv, cwd=validation_copy)
    ruff_result = run_fixed_argv(ruff_target_argv, cwd=validation_copy)
    append_checkpoint(changed_paths, hashes=current, error=failed + errors + lint_errors)
    delete(validation_copy)
    previous = current
```

### 局限性
- `codex exec` 未暴露 `--max-turns`；应使用外部进程超时/预算，而不是把一个 top-level turn 截成伪轮次
- hook 通过 `-c hooks.PostToolUse=...` 注入；观察器输出和验证镜像必须在
  workspace 外，避免审计测试改变 agent 可见状态
- JSONL `file_change` 仍保留用于平台事件审计，但指标以文件系统哈希为准，可覆盖 shell/MCP 间接写入

---

## 二、CodeBuddy（Agent SDK）

### 数据源

```typescript
import { query } from '@tencent-ai/agent-sdk';

const q = query({
    prompt: task_prompt,
    options: {
        permissionMode: 'bypassPermissions',
        cwd: workspace,
        model: 'gpt-5.6-luna-medium',
        maxTurns: 50,           // ✅ 直接支持
    },
});

for await (const msg of q) {
    // 处理消息流
}
```

### ResultMessage 结构（最终结果）

```typescript
{
    type: 'result',
    subtype: 'success' | 'error_during_execution' | 'error_max_turns' | 'error_max_budget_usd',
    session_id: string,
    duration_ms: number,        // 总耗时
    duration_api_ms: number,    // API 调用耗时
    num_turns: number,          // 总对话轮次
    result: string,             // 最终文本
    total_cost_usd: number,     // 花费
    usage: {
        input_tokens: number,
        output_tokens: number,
        cache_read_input_tokens?: number | null,
        cache_creation_input_tokens?: number | null,
    },
    permission_denials: PermissionDenial[],
}
```

### 消息流结构（逐轮追踪）

```typescript
for await (const msg of q) {
    if (msg.type === 'assistant') {
        for (const block of msg.message.content) {
            if (block.type === 'tool_use') {
                // block.name: 'write_to_file' | 'replace_in_file' | ...
                // block.input: { filePath: string, ... }
            } else if (block.type === 'tool_result') {
                // block.content: 工具执行结果
            }
        }
    }
    if (msg.type === 'result') {
        // 最终统计
    }
}
```

### 5 项指标能力

| 指标 | 可采集 | 采集方式 |
|------|:---:|------|
| **CNV-4 Token 消耗** | ✅ | `ResultMessage.usage.input_tokens + output_tokens`（含 cache 分层） |
| **CNV-2 收敛稳定性** | ✅ | SDK `hooks.PostToolUse` 同步 callback 调用同一个内容指纹采集器 |
| **CNV-3 轮次有效率** | ✅ | 同 CNV-2，基于误差序列 |
| **OSC-1 震荡位置** | ✅ | 使用平台无关 checkpoint 中的实际变化路径与哈希；ToolUseBlock 仅交叉审计 |
| **EXP-1 范围漂移** | ✅ | 实际变化路径 vs `allowed_paths` |
| **OSC-2 震荡严重度** | ✅ | 同 OSC-1 |
| **DEC-2 验证步骤数** | ✅ | 统计观察器 validation 记录，并可从 ToolUseBlock 补充 agent 主动验证次数 |

### 中间快照注入方案

```typescript
const q = query({
  prompt,
  options: {
    cwd: workspace,
    maxTurns: 50,
    settingSources: ['project'],
    hooks: { PostToolUse: [{ matcher: '*', hooks: [captureIfManifestChanged] }] }
  }
});
for await (const msg of q) if (msg.type === 'result') saveUsageAndDuration(msg);
```

### 优势
- ✅ `maxTurns` 原生支持
- ✅ `num_turns` 直接在 `ResultMessage` 中暴露
- ✅ `usage` 原生支持（含 cache 分层）
- ✅ SDK 可编程控制——中间快照注入最方便

---

## 三、能力矩阵总览

| 指标 | Codex (`--json`) | CodeBuddy (SDK) |
|------|:---:|:---:|
| **Token 消耗 (CNV-4)** | ✅ `turn.completed.usage` | ✅ `ResultMessage.usage` |
| **对话轮次** | ✅ 计数 `turn.started` | ✅ `ResultMessage.num_turns` |
| **耗时** | ❌ 不在事件中 | ✅ `duration_ms` |
| **花费** | ❌ 不在事件中 | ✅ `total_cost_usd` |
| **文件修改追踪 (OSC)** | ✅ PostToolUse + manifest；JSONL 交叉审计 | ✅ PostToolUse + manifest；ToolUseBlock 交叉审计 |
| **测试运行追踪 (DEC-2)** | ✅ `item.type="command_execution"` | ✅ `ToolUseBlock` |
| **范围漂移 (EXP-1)** | ✅ changed paths vs `allowed_paths` | ✅ 同左 |
| **中间快照注入** | ✅ 同步 PostToolUse hook | ✅ SDK PostToolUse callback |
| **maxTurns 控制** | ⚠️ 未暴露，需脚本限制 | ✅ `QueryOptions.maxTurns` |

---

## 四、建议采集方案

### Codex 方案

```bash
# 采集脚本伪代码
python -m harness.codex_runner --config run.json --prompt-file prompt.txt
```

`harness/codex_runner.py`：
- 解析 JSONL 流以提取 usage 和平台审计事件
- 同步 `PostToolUse` → 比较工作区 manifest；有变化才在一次性镜像中执行固定验证
- `item.changes[].path` 与实际 changed paths 交叉核对
- 最终 → 输出 `metrics.json`（token、mutation rounds、误差、漂移、震荡）

### CodeBuddy 方案

```typescript
// 采集脚本伪代码
const metrics = await runWithMetrics({
    prompt: taskPrompt,
    workspace: workspace,
    allowedPaths: ['src/search.py'],
    checkpoint: 'post-tool-use-if-manifest-changed',
});

// metrics 直接包含：
// { rounds, tokenUsage, fileChanges, scopeDrift, oscillations, testSnapshots }
```

### 两种方案均能采集的指标总计

| 类别 | 采集后支持的指标 | 之前状态 |
|------|---------|:---:|
| Token 消耗 | CNV-4 | ❌→✅ |
| 收敛稳定性 | CNV-2 | ❌→✅ |
| 轮次有效率 | CNV-3 | ❌→✅ |
| 震荡位置/严重度 | OSC-1, OSC-2 | ❌→✅ |
| 范围漂移率 | EXP-1 | ❌→✅ |
| 验证频率 | DEC-2 | ❌→✅ |
| 无效编辑率 | EXP-2 | ❌→✅ |
| 文件重复触碰率 | EXP-3 | ❌→✅ |

**结论**：之前标记为"暂未采集"的中间快照类指标，在两平台上**均已实现采集路径**。两端共享同一个 Python 采样/归约器，平台适配层只负责 hook 与 usage/event 提取。

---

## 五、下一步行动

1. ✅ `harness/snapshot.py`：内容指纹、固定验证命令、checkpoint JSONL
2. ✅ `harness/codex_runner.py`：`codex exec --json` + PostToolUse
3. ✅ `harness/codebuddy_runner.mjs`：Agent SDK + PostToolUse
4. ✅ `harness/metrics.py`：CNV/EXP/OSC/DEC 归约
5. ✅ `run_config.yaml` 与 `task_suite.json`：主套件、allowed paths、禁止 agent 自报数值
