# 批次运行协议

1. 定位仓库根目录和 `cel-eval-mock-project`。
2. 读取 `meta_plan/experiment-isolation.md`、`task_suite.json` 和
   `harness/README.md`；不要读取历史批次来指导 worker。
3. 在评测项目目录运行：

   ```powershell
   python _runner.py batch <batch-id> <platform> <suite>
   ```

   已存在的批次必须失败，禁止删除或复用。

4. 读取新批次的 `batch-manifest.json`。按任务随机化或交替两组顺序，把顺序及
   随机种子写入 `<batch-root>/run-order.json`。
5. 对清单中的每个运行单元，直接使用其 config 和 prompt：

   ```powershell
   # Codex
   python -m harness.codex_runner --config <config> --prompt-file <prompt>

   # CodeBuddy
   node harness/codebuddy_runner.mjs --config <config> --prompt-file <prompt>
   ```

6. 两组保持相同模型、权限和预算。每次 runner 调用必须创建新 worker session。
   不替 worker 修改文件，不根据前一组结果改变后一组。
7. 单个运行失败时保留产物并记录失败。禁止在同一结果目录重跑；重试必须使用新
   batch ID。
8. 全部完成后运行：

   ```powershell
   python _runner.py verify_batch <batch-root>
   python generate_comparison.py <batch-root>\results
   ```

9. 若用户要求审计，转入 `references/audit.md`；否则只汇报客观完成状态和路径。
