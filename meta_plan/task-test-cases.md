# CEL A/B 评价 —— 任务测例

> 每个测例需在**完全相同的初始工程快照**下，由对照组和实验组分别独立执行。
> 任务描述对两组完全相同，仅在实验组中额外添加 CEL 触发词（见 `test-prompts.md`）。

---

## 测例总览

| 编号 | 领域 | 任务类型 | 复杂度 | 预估最小修改行数 |
|------|------|----------|:------:|:----------------:|
| T01 | 代码开发 | Bug 修复（单文件） | 简单 | ~5 |
| T02 | 代码开发 | Bug 修复（跨文件） | 中等 | ~20 |
| T03 | 代码开发 | 功能实现 + 测试编写 | 中等 | ~40 |
| T04 | 代码开发 | 修复 + 重构混在一起的风险 | 中等 | ~30 |
| T05 | 测试工程 | 失败测试修复 | 中等 | ~25 |
| T06 | 测试工程 | 覆盖率缺口补充 | 简单 | ~15 |
| T07 | 日志调试 | 从日志定位根因 | 中等 | ~10 |
| T08 | 代码审查 | 处理 Review Comments | 中等 | ~30 |
| T09 | 文档编写 | 文档与代码同步 | 简单 | ~10 |
| T10 | Harness 工程 | CI 配置修复 | 中等 | ~15 |
| T11 | 架构设计 | 模块拆分与接口定义 | 复杂 | ~60 |
| T12 | 项目设计 | 需求澄清与风险清单 | 复杂 | ~50（计划文档） |
| T13 | 交叉验证 | 计划文档与代码一致性核对 | 中等 | ~20 |
| T14 | 多域组合 | Bug 修复 + 测试补全 + 文档同步 | 复杂 | ~50 |
| T15 | 震荡易发 | 经验上易导致 Agent 震荡的任务 | 复杂 | ~30 |

---

## 测例详情

### T01 · 代码开发 · 单文件 Bug 修复

- **任务描述**：
  > `src/user_service.py` 中 `get_user_by_id` 函数在传入不存在的 user_id 时抛出 `NoneTypeError`（第 42 行访问 `user.name`），请修复它。
- **初始工程状态**：
  - 测试文件 `tests/test_user_service.py` 中有 `test_get_user_not_found` 失败（期望返回 None 或抛 UserNotFoundError）
  - 另有 3 个测试全部通过
  - 无 lint/类型错误
- **期望完成状态**：
  - `test_get_user_not_found` 通过
  - 全部 4 个测试通过
  - 未修改 `get_user_by_id` 的正常路径行为
- **成功判定**：
  - 全量测试通过
  - diff 仅在 `src/user_service.py` 的 ≤1 个函数内
- **复杂度**：简单
- **预估最小修改行数**：~5 行（添加 None 检查 + 异常或返回 None）

---

### T02 · 代码开发 · 跨文件 Bug 修复

- **任务描述**：
  > `src/payment.py` 的 `process_payment` 函数在扣款成功后调用 `src/notification.py` 的 `send_receipt` 发送收据。但 `send_receipt` 需要 `user_email` 参数，当前调用只传了 `amount`。另外，当 `send_receipt` 抛异常时应记录日志并继续（不应回滚支付）。请修复。
- **初始工程状态**：
  - `tests/test_payment.py` 中 `test_payment_with_receipt` 失败（参数错误）
  - `tests/test_payment.py` 中 `test_payment_receipt_failure_does_not_rollback` 失败
  - 其余 5 个支付测试通过
- **期望完成状态**：
  - 全部 7 个测试通过
  - `process_payment` 正确传递 `user_email`
  - `send_receipt` 异常被捕获、记录日志、不传播
- **成功判定**：
  - 全量测试通过
  - diff 仅在 `src/payment.py` 和 `src/notification.py`（最多加点日志配置）
- **复杂度**：中等
- **预估最小修改行数**：~20 行

---

### T03 · 代码开发 · 功能实现 + 测试编写

- **任务描述**：
  > 在 `src/calculator.py` 中实现 `divide(a, b)` 函数，当 b=0 时抛出 `DivisionByZeroError`。然后编写测试覆盖正常除法和除零两种情况。
- **初始工程状态**：
  - `src/calculator.py` 中 `divide` 函数体为 `pass`
  - `src/calculator.py` 中 `add`, `subtract`, `multiply` 已实现且测试通过（5 个测试）
  - `DivisionByZeroError` 已在 `src/errors.py` 中定义
- **期望完成状态**：
  - `divide(a, b)` 实现正确
  - b=0 时抛 `DivisionByZeroError`
  - 测试文件中有 ≥2 个新增测试且全部通过
- **成功判定**：
  - 全量测试 ≥7 个，全部通过
  - 测试覆盖正常路径和异常路径
- **复杂度**：中等
- **预估最小修改行数**：~40 行（实现 ~10 行 + 测试 ~30 行）

---

### T04 · 代码开发 · 修复中混入重构（风险场景）

- **任务描述**：
  > `src/data_processor.py` 中 `transform_data` 函数在处理空列表时返回 `None` 而非 `[]`，导致调用方 `src/report.py` 中 for 循环报错。请只修复空列表处理，**不要做其他改动**。
- **初始工程状态**：
  - `tests/test_data_processor.py` 中 `test_transform_empty_list` 失败
  - `src/data_processor.py` 有 ~200 行代码，包含多处风格问题但功能正确
  - `src/report.py` 依赖 `transform_data` 返回 list
- **期望完成状态**：
  - `test_transform_empty_list` 通过
  - 其余测试全部通过（6 个测试）
  - `transform_data` 的其他分支行为不变
  - **未修改无关文件**、未做代码风格重构
- **成功判定**：
  - 全量测试通过
  - diff **仅在** `src/data_processor.py` 中 ≤1 个函数，修改行数 ≤10
  - 无 lint 格式变化（说明未顺手格式化）
- **关键观察**：对照组是否在不必要时做了额外重构（范围漂移）
- **复杂度**：中等
- **预估最小修改行数**：~3-5 行

---

### T05 · 测试工程 · 失败测试修复

- **任务描述**：
  > 请分析以下测试失败并修复。`tests/test_auth.py` 中 3 个测试失败，`tests/test_session.py` 中 1 个测试失败。不要修改被测代码，只修改测试本身（使测试正确反映预期行为）或者修复被测代码中的 bug（如果 bug 在代码中）。
- **初始工程状态**：
  - `test_auth.py` 失败簇 1（2 个测试）：被测代码 `auth.py` 中 `validate_token` 对过期 token 返回 200 而非 401 —— 代码 bug
  - `test_auth.py` 失败簇 2（1 个测试）：测试断言 `assert result == "admin"` 但代码返回 `"Admin"` —— 测试 bug（大小写）
  - `test_session.py` 失败（1 个测试）：竞态条件导致偶尔失败 —— Flaky 测试
- **期望完成状态**：
  - 全部测试通过（无 skip/xfail）
  - Flaky 测试应被修复（如加 mock 或重试逻辑），而非简单 skip
  - 代码 bug 被修复（`validate_token` 返回正确状态码）
  - 测试 bug 被修复（断言修正为大小写不敏感或代码统一）
- **成功判定**：
  - 全量测试通过，连续运行 3 次不出现 Flaky 失败
  - 无测试被删除或 skip
- **复杂度**：中等
- **预估最小修改行数**：~25 行

---

### T06 · 测试工程 · 覆盖率缺口补充

- **任务描述**：
  > `src/string_utils.py` 中 `truncate(text, max_len)` 函数在 `text` 为 `None` 时、`max_len` 为负数时、以及 `text` 为多字节字符时的行为未覆盖。请补充测试覆盖这三种情况。
- **初始工程状态**：
  - `tests/test_string_utils.py` 有 3 个测试覆盖了正常截断、短文本不截断、精确长度
  - 覆盖率报告显示 3 个分支未覆盖
  - `truncate` 函数代码正确
- **期望完成状态**：
  - 新增 ≥3 个测试，分别覆盖 None / 负数 / 多字节字符
  - 全部测试通过
  - 覆盖率上升 ≥25 个百分点
- **成功判定**：
  - 全部测试通过
  - 覆盖率提升达标
- **复杂度**：简单
- **预估最小修改行数**：~15 行

---

### T07 · 日志调试 · 从日志定位根因

- **任务描述**：
  > 生产环境 `logs/error.log` 中频繁出现 `ConnectionRefusedError`（见附件日志片段）。请分析日志、定位根因、修复问题。注意：不要猜测，逐步排查。
- **初始工程状态**：
  - `logs/error.log` 包含约 50 行日志，其中：
    - 真正根因：`db_config.py` 中数据库端口从 5432 被错误改为 5433（最近 commit 引入）
    - 同时有另一条无关的网络超时日志（干扰项）
    - 级联错误：`db_connection.py` → `query_builder.py` → `api_handler.py`
  - 测试环境可正常连接数据库（使用不同配置），所以不是数据库宕机
- **期望完成状态**：
  - 日志中的第一个有意义错误被正确识别（`ConnectionRefusedError` from `db_connection.py` 连接 5433）
  - 根因定位到 `db_config.py` 端口配置错误
  - 修复端口配置 → 连接恢复
  - 排除无关的网络超时干扰
- **成功判定**：
  - diff 修改了 `db_config.py` 端口（从 5433 → 5432）
  - Agent 输出中包含了明确的假设→排除→确认的推理链
  - 未修改与根因无关的文件
- **关键观察**：对照组是否直接猜测并修改错误位置，还是按推理链逐步排查
- **复杂度**：中等
- **预估最小修改行数**：~10 行

---

### T08 · 代码审查 · 处理 Review Comments

- **任务描述**：
  > 以下是对 PR #42 的 5 条 Review Comments。请逐一处理（修改代码或回复解释），不要扩大 PR 范围。
  > 1. [阻塞] `src/api.py:120` 缺少输入校验，SQL 注入风险
  > 2. [建议] `src/api.py:150` 变量命名 `x` → `user_count`
  > 3. [建议] `src/utils.py:30` 函数缺少 docstring
  > 4. [疑问] `src/config.py:10` 为什么默认 timeout 为 5 秒？请解释
  > 5. [阻塞] `tests/test_api.py` 缺少对 401 未授权场景的测试
- **初始工程状态**：
  - PR #42 包含 4 个文件的修改（api.py, utils.py, config.py, test_api.py）
  - 当前 CI 通过（仅有的测试通过）
  - Review Comments 如上
- **期望完成状态**：
  - Comment 1：添加输入校验（参数化查询或白名单校验）
  - Comment 2：变量重命名
  - Comment 3：添加 docstring
  - Comment 4：回复解释 timeout=5s 的原因（业务需求：外部 API SLA 为 3s，5s 有余量）
  - Comment 5：添加 401 测试用例
  - PR 范围不扩大，不修改其他文件
- **成功判定**：
  - 5 条评论全部处理（修改或回复）
  - CI 仍然通过
  - 新增 401 测试通过
  - 未引入新文件或修改无关文件
- **复杂度**：中等
- **预估最小修改行数**：~30 行

---

### T09 · 文档编写 · 文档与代码同步

- **任务描述**：
  > `README.md` 中的安装步骤、CLI 命令示例与当前代码不一致。请更新 README 使其匹配代码实际行为。具体不一致点：安装命令使用了旧版 pip 语法；CLI 示例中的 `--output-dir` 参数已改名为 `--out`；示例输出格式已变化。
- **初始工程状态**：
  - `README.md` 包含 3 处过时内容
  - `src/cli.py` 中 `--out` 参数正确
  - `setup.py` 使用新的安装方式
  - 文档构建（如 mkdocs）可正常生成
- **期望完成状态**：
  - README 中安装命令可执行
  - CLI 示例命令可执行且输出正确
  - 文档与代码无矛盾
- **成功判定**：
  - README 中所有命令可复制粘贴执行且成功
  - diff 仅在 README.md，修改行数合理
- **复杂度**：简单
- **预估最小修改行数**：~10 行

---

### T10 · Harness 工程 · CI 配置修复

- **任务描述**：
  > CI pipeline（`.github/workflows/ci.yml`）最近 3 次运行失败。初步判断：Python 版本依赖未锁定（测试在 3.11/3.12 之间行为不一致）、一个 job 因缺少 `DATABASE_URL` 环境变量而失败。请修复 CI 配置使其稳定可复现。
- **初始工程状态**：
  - `ci.yml` 中 `python-version: "3.x"` （模糊版本）
  - `tests` job 缺少 `DATABASE_URL` 环境变量
  - 有 1 个 `lint` job 正常通过
  - `requirements.txt` 未锁定依赖版本
- **期望完成状态**：
  - Python 版本锁定为 `"3.11"`
  - `DATABASE_URL` 环境变量添加（使用 CI secrets 或默认值）
  - `requirements.txt` 中依赖锁定到具体版本
  - 本地可模拟 CI 命令并成功运行
- **成功判定**：
  - `ci.yml` 配置正确
  - 本地运行 `pytest` 通过
  - 依赖版本全部固定（`pip freeze` 可复现）
- **复杂度**：中等
- **预估最小修改行数**：~15 行

---

### T11 · 架构设计 · 模块拆分与接口定义

- **任务描述**：
  > `src/monolith.py` 是一个 400 行的单文件模块，混合了认证、数据库查询、缓存逻辑。请设计将其拆分为 `auth/`, `db/`, `cache/` 三个模块的方案，定义接口，写入 `docs/architecture.md`。**先设计方案，再实施**。
- **初始工程状态**：
  - `src/monolith.py` 400 行，所有逻辑混杂
  - 10 个现有测试（集成测试，测试 monolith 对外行为）
  - `docs/` 目录为空
- **期望完成状态**：
  - `docs/architecture.md` 含：模块职责说明、接口定义（函数签名）、数据流、ADR（为什么这样拆分）
  - 代码已按方案拆分到 `auth/`, `db/`, `cache/`
  - 全部 10 个测试仍通过（对外行为不变）
  - 新增 ≥2 个模块级单元测试
- **成功判定**：
  - 架构文档完整且可指导实现
  - 代码已拆分且全部测试通过
  - 公共接口定义清晰（可被其他模块导入使用）
- **复杂度**：复杂
- **预估最小修改行数**：~60 行（架构文档 + 拆分后的代码调整）

---

### T12 · 项目设计 · 需求澄清与风险清单

- **任务描述**：
  > 以下是新功能"用户通知中心"的原始需求（一段自然语言描述，包含模糊点和冲突）。请梳理需求：解决冲突、明确非目标、列出风险及缓解策略、定义可测试的验收标准。输出到 `docs/notification-center-spec.md`。**不要写代码**。
- **初始工程状态**：
  - `docs/notification-center-raw-requirements.md` 包含约 300 字的模糊需求：
    - "支持邮件和短信通知" —— 短信通知是否需要？未明确
    - "实时推送" 和 "每天汇总发送" —— 冲突需求
    - "支持所有用户" 但未说明权限模型
    - 未定义消息去重策略
    - 未定义失败重试策略
- **期望完成状态**：
  - 冲突需求已解决（选择了实时推送 or 汇总，或明确两者并存的条件）
  - 非目标明确列出
  - 风险清单含 ≥5 项（含缓解策略）
  - 验收标准 ≥8 条，每条可测试
  - 假设列表列出所有未确认项
- **成功判定**：
  - 规格文档包含以上全部要素
  - 无未解决的冲突需求
  - 验收标准可以被测试人员直接使用
- **复杂度**：复杂
- **预估最小修改行数**：~50 行文档

---

### T13 · 交叉验证 · 计划文档与代码一致性核对

- **任务描述**：
  > `docs/plan.md` 记录了当前项目的实现计划和完成状态（每个条目标记为 done/undone）。请逐一核对计划标记与代码实际状态是否一致。对于不一致的条目，修正计划标记。对于已标记 done 但缺少自动化验证证据的条目，加注"需验证"。
- **初始工程状态**：
  - `docs/plan.md` 含 15 个功能条目，其中 10 个标记 done、5 个标记 undone
  - 实际代码中：
    - 2 个 done 项未完全实现（标记错误：over-estimate）
    - 1 个 undone 项实际已完成（标记错误：under-estimate）
    - 1 个 done 项实现有质量缺陷（标记应为 partial）
    - 3 个 done 项没有对应测试（缺乏验证证据）
  - 其余标记正确
- **期望完成状态**：
  - 计划文档中标记全部与代码实际一致
  - 修正了 over-estimate / under-estimate / partial 标记
  - 缺乏验证证据的项加注标记
  - 未修改计划条目**内容**（只修正了标记状态）
- **成功判定**：
  - `docs/plan.md` 中所有 done/undone 标记与代码实际一致
  - 无遗漏或误判
  - diff 仅在 plan.md，且只涉及标记修正
- **复杂度**：中等
- **预估最小修改行数**：~20 行（计划标记修正）

---

### T14 · 多域组合 · Bug 修复 + 测试 + 文档同步

- **任务描述**：
  > `src/export.py` 中 `export_csv` 函数在数据为空时崩溃（Bug）。请修复该 Bug，补充缺失的测试，并同步更新 `README.md` 中关于 CSV 导出的说明（缺少空数据处理的行为描述）。
- **初始工程状态**：
  - `tests/test_export.py` 中 `test_export_csv_empty_data` 失败（Bug）
  - `tests/test_export.py` 中缺少 `test_export_csv_special_chars` 测试（测试缺口）
  - `src/export.py` 中 `export_csv` 对空列表无防御
  - `README.md` 中未说明空数据时的行为
- **期望完成状态**：
  - `export_csv` 空数据处理正确（返回空 CSV 头或空字符串，不崩溃）
  - `test_export_csv_empty_data` 通过
  - 新增 `test_export_csv_special_chars` 通过
  - README 增加空数据行为说明
- **成功判定**：
  - 全量测试通过（≥ 新增 2 个）
  - README 中空数据行为描述准确
  - 三个修改（代码/测试/文档）全部完成
- **复杂度**：复杂
- **预估最小修改行数**：~50 行

---

### T15 · 震荡易发 · 经验上易导致 Agent 循环的任务

- **任务描述**：
  > `src/math_utils.py` 中 `calculate_statistics` 函数在输入包含 None 值时行为不一致：有时返回部分结果、有时抛异常、有时返回错误值。请在**不改变对外接口签名**的前提下，统一其行为（建议：None 值跳过，返回剩余数据的统计结果），并修复所有相关测试。
- **初始工程状态**：
  - `src/math_utils.py` 的 `calculate_statistics` 函数 ~50 行，包含多个条件分支
  - 7 个测试，其中 3 个失败（不同失败原因），2 个结果与预期偏差较小，2 个通过
  - 代码中有"修一个断一个"的隐患（多个条件分支相互影响）
- **期望完成状态**：
  - 全部 7 个测试通过
  - None 值被统一跳过
  - 函数签名不变
  - 没有因修复引入新的回归
- **关键观察**：
  - 对照组是否陷入"A 测试通过了但 B 测试又失败了"的修复-回滚循环
  - 实验组是否能通过最小更新逐轮降低失败数
- **复杂度**：复杂（震荡风险高）
- **预估最小修改行数**：~30 行

---

## mock 项目生成方案

### 项目来源

`cel-eval-mock-project` 不是"凭空手写"的，而是由两层构造：

```
第一层：base 项目（main 分支）
  └── 一个完全正确、测试全过的 Python 项目，包含所有 15 个任务涉及的模块

第二层：任务分支（从 main 派生）
  └── 每个任务引入"刻意的缺陷"，形成 task/{Tid}-init 分支
      task/{Tid}-expected 分支为人工编写/脚本生成的校正后版本
```

### 第一层：base 项目（`main` 分支）

`main` 分支上**所有代码正确、所有测试通过、无 lint/类型错误、CI 正常、文档与代码一致、日志正常**。这是所有任务的共同祖先。

目录结构与上文 mock 项目建议一致。

### 第二层：任务分支生成规则

每个 `task/{Tid}-init` 分支从 `main` 派生，通过**特定的文件替换/修改**引入缺陷。

#### 生成方式

方式一（推荐）：**脚本生成**。写一个 `generate_task_branches.py`，对每个 task 执行：
```bash
git checkout -b task/{Tid}-init main
# 应用针对该 task 的缺陷 patch
git apply tasks/patches/{Tid}-init.patch
git commit -m "task/{Tid}: introduce defects"
git checkout -b task/{Tid}-expected task/{Tid}-init
git apply tasks/patches/{Tid}-expected.patch
git commit -m "task/{Tid}: expected fix"
```

方式二（备选）：**手动创建**。在 main 上 checkout 新分支，手动引入缺陷后 commit。

#### 各任务缺陷注入规则

| 任务 | init 分支需引入的缺陷 |
|------|---------------------|
| T01 | `user_service.py:get_user_by_id` 缺少 None 检查，`test_get_user_not_found` 的断言对应 bug 行为（期望抛异常或返回 None） |
| T02 | `payment.py:process_payment` 调用 `send_receipt` 时少传 `user_email`；`send_receipt` 异常未捕获 |
| T03 | `calculator.py:divide` 函数体为 `pass`；`test_divide` 存在但期望的正确行为已写好 |
| T04 | `data_processor.py:transform_data` 空列表返回 None 而非 []；`report.py` 依赖 list 的 for 循环 |
| T05 | `auth.py:validate_token` 过期 token 返回 200 而非 401；`test_auth.py` 一个断言大小写错误；`test_session.py` 有 Flaky 依赖 |
| T06 | `string_utils.py:truncate` 函数正确但测试只覆盖 3 种正常情况，缺 3 种边界 |
| T07 | `db_config.py:DATABASE_PORT = 5433`（应为 5432）；`logs/error.log` 含 50 行连接失败日志 + 无关网络超时噪声 |
| T08 | `api.py:120` 无输入校验；`api.py:150` 变量命名 `x`；`utils.py:30` 缺 docstring；`test_api.py` 缺 401 测试 |
| T09 | `README.md` 安装命令写 `pip install .`（过时）而非实际方式；CLI 示例用 `--output-dir`（已改名 `--out`） |
| T10 | `ci.yml` 中 `python-version: "3.x"`；`tests` job 缺 `DATABASE_URL`；`requirements.txt` 无版本锁定 |
| T11 | `monolith.py` 中认证/数据库/缓存混杂（但功能正确，10 个集成测试全过）；`docs/architecture.md` 不存在 |
| T12 | `docs/notification-center-raw-requirements.md` 含冲突需求、模糊描述、缺失非目标 —— 从 main 分支新增此文件即可 |
| T13 | `docs/plan.md` 含 15 条目，其中 3 个标记 done 但实际未完成/有质量问题，1 个标记 undone 但已完成 |
| T14 | `export.py:export_csv` 空列表无防御（崩溃）；缺 `test_export_csv_special_chars`；README 未说明空数据行为 |
| T15 | `math_utils.py:calculate_statistics` 多个条件分支处理 None 时行为不一致；7 个测试中有 3 失败 + 2 偏差 |

### 关键约束

- **base 项目 (`main`) 必须真实可运行**：`pytest` 全通过、`ruff check` 零错误、`mypy` 零错误
- **每个 init 分支的缺陷必须可独立修复**：T01 的缺陷不影响 T02 的正常功能
- **expected 分支必须经过人工验证**：全量测试通过，且修改范围符合"最小修改"标准
- **每个 task 的 init 和 expected 之间的 diff，严格等于该任务的"最少必要修改"**
- **mock 项目所有依赖均使用标准库或轻量第三方库（pytest）**，避免复杂环境搭建
