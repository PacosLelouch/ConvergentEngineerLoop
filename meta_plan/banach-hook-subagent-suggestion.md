可以，而且**很应该拆一部分出来做成 hook 或 subagent**。但要注意分工：

> **Hook 适合做“硬约束、自动检查、自动验证、自动阻断”。**  
> **Subagent 适合做“专项分析、计划、审查、调试、文档同步”等需要推理的工作。**

也就是说，不建议把“Banach / 收敛式迭代”整体做成一个 subagent；更好的方式是：

```text
主 Agent：负责执行任务
Hooks：负责强制检查、验证、回滚、停止
Subagents：负责专项分析和建议
Skill / Reference：负责给各角色提供规范
```

---

# 1. 总体判断

## 适合做 hook 的部分

这些内容更适合做 hook，因为它们应该被**稳定、自动、可重复地执行**：

```text
最小修改检查
无关文件检查
测试 / 构建 / lint 自动运行
失败数统计
误差度量计算
回滚触发
危险命令拦截
大 diff 拦截
停止条件检查
震荡检测
```

Hook 的作用是防止 Agent “嘴上说收敛，实际乱改”。

---

## 适合做 subagent 的部分

这些内容更适合做 subagent，因为它们需要语义理解、推理、归纳、判断：

```text
项目设计澄清
架构审查
修复计划制定
日志根因分析
测试失败聚类
文档一致性分析
Review comments 分类
CI / Harness 失败归因
```

Subagent 的作用是让主 Agent 获得更专业、更隔离的分析结果。

---

# 2. 推荐架构

可以设计成：

```text
Convergent Engineering System
├── Skill / References
│   ├── 项目设计
│   ├── 架构设计
│   ├── 代码开发
│   ├── 文档编写
│   ├── 日志调试
│   ├── 测试工程
│   ├── 代码审查
│   └── Harness 工程
│
├── Hooks
│   ├── 计划前检查
│   ├── 修改前守卫
│   ├── 修改后验证
│   ├── 误差度量更新
│   ├── 回滚触发
│   ├── 震荡检测
│   └── 停止条件检查
│
└── Subagents
    ├── 收敛计划 Agent
    ├── 测试分析 Agent
    ├── 日志调试 Agent
    ├── 代码审查 Agent
    ├── 文档同步 Agent
    ├── 架构评审 Agent
    └── Harness 稳定性 Agent
```

核心思想是：

$$
x_{t+1}=T(x_t)
$$

但是由 hooks / harness 去判断是否满足：

$$
E(x_{t+1}) \leq E(x_t)
$$

而不是只让 LLM 自己声称“我已经改好了”。

---

# 3. 哪些最适合做 Hook？

下面这些是最有价值的 hook。

---

## 3.1 Plan 前 Hook：要求生成收敛计划

适合事件：

```text
任务开始前
进入 Plan 模式前
用户请求较复杂修改时
```

作用：

```text
检查是否已有计划
检查计划是否包含验证方式
检查是否定义完成条件
高风险任务强制先计划
```

可以做成规则：

```text
如果任务涉及跨文件修改、数据库、鉴权、安全、CI、公共 API，则必须先输出计划，不能直接改代码。
```

Hook 输出给 Agent 的提示可以很短：

```text
该任务可能有风险。请先给出收敛式计划：当前状态、目标状态、最小步骤、验证方式、回滚条件。暂时不要修改代码。
```

---

## 3.2 Pre-Edit Hook：修改前守卫

适合在 Agent 准备编辑文件前触发。

检查：

```text
是否有明确目标
是否有计划
是否修改了无关文件
是否试图大范围重写
是否修改敏感文件
是否同时做重构和功能开发
```

可以阻断的行为：

```text
一次性改太多文件
全仓库格式化
删除测试
削弱断言
无理由改公共接口
修改 lockfile 但未说明原因
修改 CI 配置但未说明影响
```

示例规则：

```text
如果本轮 diff 涉及超过 N 个文件，且用户没有明确要求大改，则阻断并要求缩小修改范围。
```

```text
如果删除测试文件或降低断言强度，则要求 Agent 解释原因并请求用户确认。
```

---

## 3.3 Post-Edit Hook：修改后验证

这是最重要的 hook 之一。

编辑完成后自动运行：

```text
相关测试
类型检查
Lint
构建
文档示例检查
CLI help 检查
```

根据任务类型选择不同验证。

例如代码任务：

```text
pytest 相关测试
mypy / pyright
ruff / eslint
npm test / go test / cargo test
```

文档任务：

```text
README 中命令是否存在
示例命令是否可运行
文档构建是否通过
```

CI / Harness 任务：

```text
本地模拟 CI 命令
依赖锁检查
随机种子检查
环境变量检查
```

Hook 的关键作用：

```text
不要让 Agent 自己判断“应该没问题”
而是用外部信号判断
```

---

## 3.4 Error Metric Hook：误差度量计算

这个 hook 负责把验证结果转成可比较指标。

例如代码任务：

$$
E_{\text{dev}}=
10F_{\text{test}}
+5F_{\text{build}}
+3F_{\text{type}}
+F_{\text{lint}}
$$

其中：

- $$F_{\text{test}}$$：失败测试数；
- $$F_{\text{build}}$$：构建失败数；
- $$F_{\text{type}}$$：类型错误数；
- $$F_{\text{lint}}$$：Lint 错误数。

然后比较：

$$
\Delta E=E(x_{t+1})-E(x_t)
$$

规则：

```text
如果 ΔE < 0：接受
如果 ΔE = 0：人工判断或保留低风险修改
如果 ΔE > 0：回滚或要求重新计划
```

---

## 3.5 Rollback Hook：退化自动回滚

如果 Post-Edit 验证发现：

```text
测试失败数增加
构建从通过变失败
类型错误增加
Lint 错误增加
修改了禁止文件
diff 超出范围
```

则触发：

```text
回滚本轮 patch
记录失败尝试
要求 Agent 提出更小修改
```

注意：是否自动回滚要看工具权限。有些场景可以自动：

```text
git checkout -- file
git restore .
apply reverse patch
```

高风险项目则可以只建议回滚，等待用户确认。

---

## 3.6 Dangerous Command Hook：危险命令拦截

适合拦截 Bash / shell 命令。

应拦截或要求确认：

```text
rm -rf
git reset --hard
git clean -fd
drop database
truncate table
npm publish
pip uninstall
docker system prune
修改生产配置
删除 migration
跳过 CI 的命令
```

这个 hook 和收敛式迭代关系很强，因为它防止 Agent 做不可逆大动作。

---

## 3.7 Diff Scope Hook：修改范围控制

每轮修改后检查：

```text
本轮改了多少文件？
是否都是计划内文件？
是否包含格式化噪声？
是否包含无关重构？
是否触碰公共 API？
是否触碰安全敏感路径？
```

如果超出范围：

```text
阻断
要求拆小
要求说明
或请求用户确认
```

---

## 3.8 Oscillation Hook：震荡检测

这是 Banach 思想里很关键的一部分。

检测：

```text
同一测试反复失败
同一文件被来回改
A 修复导致 B 失败，B 修复导致 A 失败
连续 N 轮误差不下降
连续 N 次回滚
```

触发后要求：

```text
停止自动修改
总结已尝试方案
列出被排除假设
请求用户决策
```

规则示例：

```text
如果连续 3 轮 E 不下降，则停止并输出诊断报告。
```

---

## 3.9 Stop Hook：完成或停止检查

任务结束前检查：

```text
是否满足验收标准？
是否运行了验证？
是否还有未说明失败？
是否有未提交的无关 diff？
是否总结了修改与风险？
```

输出：

```text
完成摘要
验证结果
剩余风险
未解决问题
建议下一步
```

---

# 4. 哪些适合做 Subagent？

Subagent 不应该负责“强制执行”，而应该负责“专项判断”。下面这些最适合。

---

## 4.1 收敛计划 Subagent

名称可以是：

```text
convergence-planner
```

中文：

```text
收敛计划 Agent
```

职责：

```text
分析任务
选择 reference
定义误差度量
拆解最小步骤
提出验证方式
列出回滚条件
识别风险
```

适合在 Codex Plan / CodeBuddy Plan 模式中使用。

输入：

```text
用户任务
当前仓库状态
失败日志
相关文件
```

输出：

```text
当前状态
目标状态
误差度量
最小迭代步骤
验证命令
回滚条件
停止条件
```

它不一定直接改代码。

---

## 4.2 测试分析 Subagent

名称：

```text
test-failure-analyst
```

职责：

```text
分析失败测试
聚类失败原因
区分产品 bug 和测试 bug
找最小复现
建议优先修复顺序
```

适合输入：

```text
pytest / jest / go test / cargo test 输出
覆盖率报告
最近 diff
```

输出：

```text
失败簇
可能根因
受影响文件
建议最小修复
验证命令
```

这个 subagent 很有价值，因为它能帮助主 Agent 不要乱修。

---

## 4.3 日志调试 Subagent

名称：

```text
debug-root-cause-analyst
```

职责：

```text
分析日志
提取 first meaningful error
列出活跃假设
排除无效假设
设计下一步实验
```

输出格式建议固定：

```text
已知事实：
未知信息：
活跃假设：
已排除假设：
下一步实验：
预期观察：
```

这个 subagent 不应该直接修代码，除非主 Agent 明确授权。

---

## 4.4 代码审查 Subagent

名称：

```text
review-convergence-agent
```

职责：

```text
逐条整理 review comments
区分必须修改 / 可以解释 / 需要用户决策
检查 diff 是否过大
检查安全、性能、可维护性问题
生成回应建议
```

输出：

```text
评论编号
处理方式
建议 patch 范围
验证方式
回复草稿
```

它适合在 PR 修改前或修改后调用。

---

## 4.5 文档同步 Subagent

名称：

```text
doc-sync-agent
```

职责：

```text
比较 README / API docs / CLI help / 代码接口
找出过期命令
找出缺失配置项
检查示例是否可运行
建议最小文档更新
```

输出：

```text
不一致项列表
建议更新段落
需要验证的命令
不应修改的文档范围
```

---

## 4.6 架构评审 Subagent

名称：

```text
architecture-reviewer
```

职责：

```text
评估模块边界
识别循环依赖
检查接口稳定性
检查技术选型影响
生成 ADR 建议
```

它适合在大改之前使用，而不是每次小 bug 都调用。

---

## 4.7 Harness 稳定性 Subagent

名称：

```text
harness-stability-agent
```

职责：

```text
分析 CI / benchmark / eval harness 失败
区分环境问题和产品问题
检查依赖锁定
检查随机种子
检查输出格式稳定性
```

输出：

```text
失败归因
不确定性来源
最小修复建议
复现命令
CI 与本地差异
```

---

# 5. Hook 和 Subagent 的分工表

| 能力 | 更适合 Hook | 更适合 Subagent |
|---|---:|---:|
| 拦截危险命令 | 是 | 否 |
| 检查 diff 是否过大 | 是 | 可辅助解释 |
| 自动运行测试 | 是 | 否 |
| 解析失败测试根因 | 可做基础解析 | 是 |
| 定义误差度量 | 可计算 | 是，负责建议 |
| 比较 $$E(x_{t+1})$$ 和 $$E(x_t)$$ | 是 | 否 |
| 自动回滚 | 是 | 否 |
| 日志根因分析 | 否 | 是 |
| Review comments 分类 | 否 | 是 |
| 文档一致性判断 | 部分可自动 | 是 |
| 震荡检测 | 是 | 可辅助总结 |
| 计划制定 | 否 | 是 |
| 停止条件强制执行 | 是 | 可辅助说明 |

一句话：

> **Hook 管纪律，Subagent 管专业判断。**

---

# 6. 最推荐优先实现的 Hook

如果只能先做几个，我建议优先做这 6 个。

## 第一优先级

```text
1. Pre-Edit 最小修改守卫
2. Post-Edit 自动验证
3. Error Metric 误差计算
4. Regression / Rollback 回滚触发
```

这四个直接决定是否真的能收敛。

---

## 第二优先级

```text
5. Dangerous Command 拦截
6. Oscillation 震荡检测
```

这两个防止 Agent 造成不可逆损害或陷入循环。

---

# 7. 最推荐优先实现的 Subagent

如果只能先做几个，建议优先做这 4 个。

```text
1. convergence-planner：收敛计划 Agent
2. test-failure-analyst：测试失败分析 Agent
3. debug-root-cause-analyst：日志根因分析 Agent
4. review-convergence-agent：Review 收敛 Agent
```

原因：

- 计划 Agent 能防止一开始走错方向；
- 测试 Agent 能提高代码修复成功率；
- 调试 Agent 能减少瞎猜；
- Review Agent 能控制 PR diff 和反馈闭环。

---

# 8. 一个推荐的执行流

可以这样组合：

```text
用户提出任务
  ↓
Plan Hook 判断是否需要先计划
  ↓
convergence-planner subagent 生成收敛计划
  ↓
主 Agent 执行第一步最小修改
  ↓
Pre-Edit Hook 检查修改范围
  ↓
应用 patch
  ↓
Post-Edit Hook 运行验证
  ↓
Error Metric Hook 计算误差变化
  ↓
如果变好：接受
如果变差：Rollback Hook 回滚
如果无改进多轮：Oscillation Hook 停止
  ↓
必要时调用 test/debug/review/doc subagent
  ↓
Stop Hook 输出总结
```

---

# 9. 示例：代码修复场景

## 使用的 Subagent

```text
convergence-planner
test-failure-analyst
```

## 使用的 Hooks

```text
Pre-Edit Hook
Post-Edit Test Hook
Error Metric Hook
Rollback Hook
Oscillation Hook
```

执行过程：

```text
1. test-failure-analyst 分析失败测试，聚类失败原因。
2. convergence-planner 制定最小修复计划。
3. 主 Agent 修改一个最小代码路径。
4. Pre-Edit Hook 检查是否越界。
5. Post-Edit Hook 运行 pytest 目标测试。
6. Error Metric Hook 比较失败数。
7. 变好则继续，变差则回滚。
```

---

# 10. 示例：日志调试场景

## 使用的 Subagent

```text
debug-root-cause-analyst
```

## 使用的 Hooks

```text
Dangerous Command Hook
Experiment Result Hook
Oscillation Hook
Stop Hook
```

执行过程：

```text
1. debug-root-cause-analyst 提取 first meaningful error。
2. 列出活跃假设和已排除假设。
3. 主 Agent 每次只做一个实验。
4. Hook 记录实验结果。
5. 如果假设空间没有减少，停止并总结。
```

这里的误差可以定义为：

$$
E_{\text{debug}}=
w_1H+w_2U+w_3R
$$

其中：

- $$H$$：活跃假设数量；
- $$U$$：未知关键信息数量；
- $$R$$：复现不确定性。

---

# 11. 示例：Review Comments 场景

## 使用的 Subagent

```text
review-convergence-agent
```

## 使用的 Hooks

```text
Diff Scope Hook
Post-Edit Test Hook
Review Resolution Hook
Stop Hook
```

执行过程：

```text
1. review-convergence-agent 将评论分类。
2. 主 Agent 每轮只处理一个 comment 或一组相关 comment。
3. Diff Scope Hook 防止无关重构。
4. Post-Edit Hook 运行相关测试。
5. Review Resolution Hook 检查哪些评论已解决。
6. Stop Hook 输出逐条回应。
```

---

# 12. 示例 Hook 规则片段

可以放到项目规则或工具 hook 配置里。

```markdown
# 收敛式修改守卫

在 Agent 修改文件前检查：

- 是否存在明确目标？
- 是否有本轮最小修改说明？
- 是否修改无关文件？
- 是否删除测试？
- 是否削弱断言？
- 是否引入新依赖？
- 是否触碰敏感文件？

如果违反规则，要求 Agent 缩小修改范围或请求用户确认。
```

---

```markdown
# 修改后验证 Hook

每次代码修改后：

1. 识别受影响文件。
2. 选择最小相关验证命令。
3. 运行验证。
4. 记录修改前后失败数。
5. 如果失败数增加，建议回滚。
6. 如果连续 3 次无改进，停止自动修改。
```

---

# 13. Subagent 描述示例

下面是一个适合放入 subagent 描述的版本。

```markdown
# 收敛计划 Agent

你是收敛计划 Agent。你的职责不是直接修改代码，而是为主 Agent 制定稳定、可验证、可回滚的执行计划。

你必须输出：

1. 当前状态；
2. 目标状态；
3. 使用的参考类型；
4. 误差度量；
5. 最小迭代步骤；
6. 每一步的验证方式；
7. 接受条件；
8. 回滚条件；
9. 停止条件；
10. 需要用户确认的问题。

原则：

- 每一步只处理一个问题簇；
- 不建议无关重构；
- 不建议删除有效测试；
- 不把假设写成事实；
- 没有验证方式的步骤应标记为高风险。
```

---

# 14. 不建议做成 Hook / Subagent 的内容

有些东西不适合拆出去。

## 不建议把 Banach 定理本身做成 subagent

例如：

```text
banach-fixed-point-agent
```

这个命名不太好，因为：

```text
太抽象
对任务帮助不直接
容易输出理论解释
不利于自然触发
```

更推荐：

```text
convergence-planner
test-failure-analyst
debug-root-cause-analyst
```

也就是按工作职责命名，而不是按数学来源命名。

---

## 不建议用 LLM Hook 做强裁决

如果 hook 可以用脚本判断，就不要让 LLM 判断。

例如：

```text
测试是否通过
diff 文件数
是否删除测试
是否出现 rm -rf
失败数是否增加
```

这些应该用确定性脚本。

LLM 更适合判断：

```text
这个失败更可能来自哪里？
这个 review comment 是否已语义解决？
这个文档是否表达清楚？
```

---

# 15. 最终建议

可以拆，而且建议这样拆：

## Hook 层

```text
计划前检查
修改前守卫
危险命令拦截
修改后验证
误差度量计算
回滚触发
震荡检测
停止条件检查
```

## Subagent 层

```text
收敛计划 Agent
测试失败分析 Agent
日志根因分析 Agent
代码审查 Agent
文档同步 Agent
架构评审 Agent
Harness 稳定性 Agent
```

## Skill 层

```text
收敛式工程迭代
项目设计参考
架构设计参考
代码开发参考
文档编写参考
日志调试参考
测试工程参考
代码审查参考
Harness 工程参考
```

最重要的一句话是：

> **把“收敛思想”做成 Skill 可以指导 Agent 怎么想；把“验证、阻断、回滚、停止”做成 Hook 才能约束 Agent 怎么做；把“测试、调试、审查、文档”等专项判断做成 Subagent，才能提高复杂任务的专业性和稳定性。**