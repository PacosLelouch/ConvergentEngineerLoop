# 批次审计协议

审计已有批次时保持只读。只允许新增缺失的程序化 comparison 和
`<batch-root>/audit-report.md`。

1. 读取 `meta_plan/experiment-isolation.md`、`task_suite.json`、
   `batch-manifest.json`。
2. 运行：

   ```powershell
   python _runner.py verify_batch <batch-root>
   ```

   若失败，将批次判为无效并停止效果结论。

3. 对清单中的每个 Control/CEL 运行检查：
   - `collector-config.json`、`prompt.txt`、`run.json`、
     `checkpoints.jsonl`、`metrics.json` 均存在；
   - 配对初始载荷相等；
   - task ID、平台、初始误差、初始 pytest 总数和验证器集合一致；
   - checkpoint、mutation round、token 均为非负数；
   - final error 能由 final validations 的 error score 重建；
   - 结果目录不位于 worker 工作区中。
4. 缺失 comparison 时运行：

   ```powershell
   python generate_comparison.py <batch-root>\results
   ```

5. 从 `metrics.json` 和 comparison 报告终点成功、误差序列、mutation rounds、
   CNV-2/3/4、EXP-1/2/3、OSC-1/2。不得使用 agent 自报或估算值。
6. 按 simple、medium、complex 分层汇总配对差值，不把定性套件混入主实验。
7. 明确区分“效果差异”“都成功但过程不同”“运行无效或样本不足”。
8. 把可追溯结论写入 `<batch-root>/audit-report.md`，注明每项数据的相对路径。
