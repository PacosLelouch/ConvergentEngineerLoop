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
| T16 | 算法重构 | 递归→迭代转换 + 大规模输入测试 | 复杂 | ~30 |
| T17 | 并发安全 | 线程安全 + 不破坏单线程性能 | 复杂 | ~50 |
| T18 | 渐进排查 | 关联 bug 需按正确顺序修复 | 复杂 | ~40 |
| T19 | 遗留重构 | 300行遗留代码重构+流式支持 | 复杂 | ~80 |
| T20 | 不完整信息 | 外部 API 文档错误，需推断真实格式 | 复杂 | ~55 |
| T21 | 可靠性语义 | 重试幂等性 + 冲突检测 + 批次原子性 | 复杂 | ~60 |
| T22 | 异步生命周期 | 异常/超时/取消的统一资源清理 | 复杂 | ~55 |

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

### T16 · 算法重构 · 递归→迭代转换

- **任务描述**：
  > `src/search.py` 中 `full_text_search` 和 `search_with_filters` 使用递归实现逐文档处理。当 documents 数量 >800 时触发 `RecursionError`（超过 Python 默认递归限制 1000）。请将两个函数改为迭代实现，函数签名和行为不变。确保 1000 和 3000 文档的搜索都能通过。
- **初始工程状态**：
  - `src/search.py` 的 `full_text_search` 使用 `_search_recursive` 尾递归逐文档检查
  - `search_with_filters` 间接调用递归函数
  - `tests/test_search.py` 中 6 个小规模正确性测试通过，2 个大规模测试（1000/3000 docs）因 RecursionError 失败
- **期望完成状态**：
  - `full_text_search` 改为迭代实现（for 循环或 while 循环）
  - `search_with_filters` 改为迭代实现
  - 全部 10 个测试通过，包括大规模文档测试
  - 函数签名不改变
- **成功判定**：
  - 全量测试通过（10 个测试）
  - diff 仅在 `src/search.py`
  - 不改动函数签名
- **关键观察**：
  - 对照组是否可能重写整个文件（过度工程），而非做最小转换
  - CEL 组的最小更新原则是否能做到精准替换递归部分
  - 递归→迭代是明确的算法模式，但尾递归转循环有其技巧性
- **复杂度**：复杂（需要理解递归→迭代的转换模式）
- **预估最小修改行数**：~30 行

---

### T17 · 并发安全 · 线程安全 + 不破坏单线程性能

- **任务描述**：
  > `src/counter.py` 中 `ThreadSafeCounter` 类的 `increment()` 和 `get()` 方法在并发场景下计数不准确（缺少同步机制）。请修复并发安全问题。约束：(1) 同步原语必须属于每个计数器实例，禁止模块级全局锁；(2) 临界区只保护实例状态；(3) 不能破坏已有的 5 个单线程测试；(4) 编写并发压力测试证明修复有效。
- **初始工程状态**：
  - `ThreadSafeCounter` 类名叫 ThreadSafe 但实际没有同步机制
  - `tests/test_counter.py` 有 5 个单线程测试全通过
  - 2 个并发测试（`test_concurrent_increment`、`test_concurrent_mixed_ops`）失败——计数不准
  - 并发压力测试缺失
- **期望完成状态**：
  - 2 个并发测试通过
  - 5 个单线程测试保持通过
  - 新增加 ≥1 个并发压力测试（≥10 线程, ≥1000 次操作）
  - 实现使用每实例细粒度锁或其他适当同步原语，不能是模块级全局锁
- **成功判定**：
  - 全量测试通过（含并发压力测试连续 5 次运行不失败）
  - 并发压力测试中最终计数值精确等于总操作数
  - 无死锁
- **关键观察**：
  - 对照组是否只会加模块级全局锁，导致不同实例相互阻塞
  - CEL 组是否能通过误差驱动找到平衡点（加锁粒度与性能的权衡）
  - 并发 bug 是否导致震荡（修了这里又坏了那里）
- **复杂度**：复杂
- **预估最小修改行数**：~50 行（同步机制 ~20 + 压力测试 ~30）

---

### T18 · 渐进排查 · 关联 bug 需按正确顺序修复

- **任务描述**：
  > 以下 3 个模块存在相互关联的 bug。修复一个会暴露另一个的测试失败。请找出 3 个 bug 的正确修复顺序，逐一修复。在开始修复前，先推理出正确顺序。
  > - `src/parser.py` 的 `parse_config` 对非法 YAML 返回空 dict 而非抛异常
  > - `src/validator.py` 的 `validate` 函数依赖 `parse_config` 返回非空 dict，空 dict 时抛 KeyError
  > - `src/writer.py` 的 `write_output` 在 `validate` 抛异常时没有清理临时文件
- **初始工程状态**：
  - `tests/test_parser.py` 中 2 个失败（非法 YAML 期望异常但返回空 dict）
  - `tests/test_validator.py` 中 3 个通过（因为单独测试时 parse_config mock 了）
  - `tests/test_writer.py` 中 1 个失败（集成测试——临时文件残留）
  - 9 个其他测试通过
- **期望完成状态**：
  - 按正确顺序修复 3 个 bug（parser → validator → writer 的依赖链要求先修 parser）
  - 全量测试通过
  - 修复顺序被正确记录在 agent 输出中
- **成功判定**：
  - 全量测试通过（15 个测试）
  - Agent 输出包含修复顺序推理链
  - 每个中间步骤的测试快照显示逐步收敛（失败数 3→1→0 而非 3→5→0）
- **关键观察**：
  - 对照组可能不先推理顺序，直接同时改 3 个文件——导致中间状态测试失败数反而上升
  - CEL 组应体现"先诊断→再规划→再执行"的收敛序列
  - 这是 CEL 过程价值的典型案例——最终的"全量测试通过"两者都能做到，但过程的混乱程度不同
- **复杂度**：复杂
- **预估最小修改行数**：~40 行（3 个模块各 ~10-15 行）

---

### T19 · 遗留重构 · 300 行遗留代码重构 + 流式支持

- **任务描述**：
  > `src/legacy_parser.py`（300 行）是一个遗留日志解析器。现需在 15 个现有测试**全部保持通过**的前提下，重构 `parse()` 函数使其支持流式输入（从 `parse(file_path)` 扩展为 `parse(source, streaming=False)`，当 `streaming=True` 时接收 `Iterable[str]` 并逐行返回解析结果）。同时写出迁移指南，说明旧调用方式如何迁移到新接口。
- **初始工程状态**：
  - `src/legacy_parser.py` 300 行，`parse(file_path: str) -> List[LogEntry]`
  - `tests/test_legacy_parser.py` 15 个测试全通过
  - 代码风格差（变量命名随意、3 个 80+ 行函数、magic number 满天飞）
  - `docs/` 下无迁移指南
- **期望完成状态**：
  - `parse(source, streaming=False)` 支持两种模式：
    - `streaming=False`：接收 `str`（文件路径），返回 `List[LogEntry]`（兼容旧接口）
    - `streaming=True`：接收 `Iterable[str]`，返回 `Iterator[LogEntry]`
  - 全部 15 个旧测试通过（无修改）
  - 新增 ≥5 个测试覆盖两种模式
  - `docs/legacy-parser-migration.md` 含迁移指南
- **成功判定**：
  - 全量测试 ≥20 个，全部通过
  - 旧测试零修改
  - 迁移指南包含迁移步骤 + 示例代码
- **关键观察**：
  - 对照组是否为了"顺手"重构代码风格而引入回归（范围漂移的风险很大）
  - CEL 组的"最小更新"协议能否在"功能扩展（允许）"和"风格重构（禁止）"之间做出正确区分
  - 在遗留代码的大文件上是否出现震荡（改了 A 函数又回到 A 函数）
- **复杂度**：复杂
- **预估最小修改行数**：~80 行（重构 ~40 + 测试 ~25 + 文档 ~15）

---

### T20 · 不完整信息 · 外部 API 文档错误，需推断真实格式

- **任务描述**：
  > 项目依赖的外部天气 API（`src/weather_client.py`）的文档描述与实际返回格式不符。文档说返回 `{"temp": float, "humidity": int}`，但生产日志显示实际返回 `{"main": {"temp": float}, "humidity": int}`（嵌套了一层 `main`）。请根据 `logs/api_responses.log` 中的真实响应数据，推断实际格式，修复 `weather_client.py` 的解析逻辑，并更新 `docs/weather-api.md` 文档使其与实际一致。**不要盲信文档**。
- **初始工程状态**：
  - `src/weather_client.py` 的 `get_weather()` 按文档格式解析，生产环境中频繁 KeyError
  - `logs/api_responses.log` 有 20 条真实 API 响应（包含正常响应 + 错误响应 + 不完整响应）
  - `tests/test_weather_client.py` 中 2 个测试失败（mock 了文档格式，实际不匹配）
  - `docs/weather-api.md` 写的格式与文档一致（错误）
- **期望完成状态**：
  - 修复 `weather_client.py` 的解析逻辑，适配真实格式
  - 处理边界情况：不完整响应（缺字段）、错误响应、嵌套路径
  - 更新 `docs/weather-api.md` 反映真实格式
  - 更新 mock 测试使其与真实格式一致
  - 全量测试通过
- **成功判定**：
  - 全量测试通过（含解析了真实日志数据的测试）
  - 边界情况处理正确（不完整响应返回合理默认值，不崩溃）
  - `docs/weather-api.md` 格式描述与代码解析逻辑一致
- **关键观察**：
  - 对照组是否直接相信任务描述中的文档（含错误信息），而不去验证日志
  - CEL 组的"外部验证优先"协议是否能促使 agent 先去读日志再动手
  - 不完整信息场景下，agent 能否在"不确定"状态下做出合理假设并记录
- **复杂度**：复杂
- **预估最小修改行数**：~55 行（解析修复 ~20 + 边界处理 ~10 + 测试更新 ~15 + 文档 ~10）

---

### T21 · 可靠性语义 · 重试幂等性与批次原子性

- **任务描述**：修复 `src/event_ledger.py`，保证相同事件重试不重复记账；相同 `event_id` 的不同内容报冲突；批次中任一事件无效或造成负余额时不保留部分更新；失败后的合法重试仍能成功。
- **初始工程状态**：顺序原地更新余额，只保存 event id；冲突被静默忽略，后续事件失败时前面的余额和幂等记录已经提交。
- **成功判定**：全量测试通过；重复重试、批内重复、冲突 id、失败回滚、失败后重试及输入验证均满足契约。
- **关键观察**：agent 是否只修某个失败断言，还是先建立“验证→暂存→原子提交”的一致模型。
- **复杂度**：复杂
- **初始信号**：6 failed / 117 passed

---

### T22 · 异步生命周期 · 异常/超时/取消的统一清理

- **任务描述**：修复 `src/async_fetcher.py`，让成功、worker 异常、超时和调用方取消都终止全部子任务并恰好关闭一次 transport；不得吞掉原异常或 `CancelledError`，空输入不得打开连接。
- **初始工程状态**：只在成功路径关闭 transport；worker 异常留下 sibling task，超时和调用方取消跳过资源清理。
- **成功判定**：五条生命周期测试全部通过，无活跃子任务或未取回 future 警告。
- **关键观察**：agent 是否只补 `except Exception`，从而漏掉 `CancelledError`，以及是否把 cleanup 放在统一 `finally`。
- **复杂度**：复杂
- **初始信号**：3 failed / 120 passed

---

## 当前可执行套件

默认测试流程只读取 `cel-eval-mock-project/task_suite.json` 的 `primary`：

`T02, T04, T05, T10, T14, T16, T17, T18, T19, T20, T21, T22`

T11/T12/T13 进入单独的 qualitative 盲评；T01/T03/T06/T07/T08/T09/T15 保留文件但默认不运行。逐项原因和正交性矩阵见 `meta_plan/task-suite-review.md`。

## mock 项目生成方案

### 项目来源

`cel-eval-mock-project` 不是"凭空手写"的，而是由两层构造：

```
第一层：base 项目
  └── 一个完全正确、123 个测试全过的 Python 项目，包含 T01-T22 涉及的模块

第二层：任务 overlay（tasks/{Tid}/init）
  └── 将缺陷文件递归合并到 base 的副本；不得替换整个 src/tests 目录
```

### 第一层：base 项目（`main` 分支）

`main` 分支上**所有代码正确、所有测试通过、无 lint/类型错误、CI 正常、文档与代码一致、日志正常**。这是所有任务的共同祖先。

目录结构与上文 mock 项目建议一致。

### 第二层：历史任务分支生成草案（已由 overlay 流程替代）

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
| T16 | `search.py:full_text_search` 和 `search_with_filters` 使用递归实现，文档 >800 时 RecursionError |
| T17 | `counter.py:ThreadSafeCounter` 无同步机制名不副实；2 个并发测试失败；并发压力测试缺失 |
| T18 | `parser.py:parse_config` 非法 YAML 返回 {} 而非异常；`validator.py:validate` 依赖非空 dict 导致 KeyError；`writer.py:write_output` 异常时残留临时文件 |
| T19 | `legacy_parser.py` 300行 `parse(file_path)` 不支持流式输入；代码风格差但功能正确（15个测试通过）；无迁移文档 |
| T20 | `weather_client.py:get_weather()` 按错误文档格式解析；`logs/api_responses.log` 含 20 条真实响应（含异常/不完整）；`docs/weather-api.md` 文档格式与真实 API 不符 |
| T21 | `event_ledger.py` 原地逐事件提交，只按 id 去重，缺少冲突检测、原子回滚与输入验证 |
| T22 | `async_fetcher.py` 只在成功路径关闭 transport，异常/超时/取消路径缺少子任务回收与关闭 |

### 关键约束

- **base 项目 (`main`) 必须真实可运行**：`pytest` 全通过、`ruff check` 零错误、`mypy` 零错误
- **每个 init 分支的缺陷必须可独立修复**：T01 的缺陷不影响 T02 的正常功能
- **expected 分支必须经过人工验证**：全量测试通过，且修改范围符合"最小修改"标准
- **每个 task 的 init 和 expected 之间的 diff，严格等于该任务的"最少必要修改"**
- **mock 项目所有依赖均使用标准库或轻量第三方库（pytest）**，避免复杂环境搭建
