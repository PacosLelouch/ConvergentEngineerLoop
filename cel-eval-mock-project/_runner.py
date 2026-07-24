"""CEL A/B 测试编排脚本。
处理文件复制、测试运行、结果采集等机械操作。
"""

import os
import sys
import shutil
import subprocess
import json
import hashlib
import re
from pathlib import Path

from harness.isolation import (
    path_digest,
    verify_config_isolation,
    verify_source_guard,
    write_source_guard,
)
from harness.snapshot import workspace_manifest

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
BASE = ROOT / "base"
TASKS = ROOT / "tasks"
SUITE_MANIFEST = ROOT / "task_suite.json"
CEL_SOURCE = PROJECT_ROOT / "_shared" / "skills" / "convergent-engineering-loop"
CEL_EVAL_SKILL_SOURCE = PROJECT_ROOT / "_shared" / "skills" / "cel-ab-evaluation"
RUNS_ROOT = Path(os.environ.get("CEL_EVAL_OUTPUT", PROJECT_ROOT / "test-runs"))
OUTPUT = RUNS_ROOT / "manual"

RUNNER_WORKING = ROOT / "_runner_working"  # 避免与 working 目录冲突

COMMON_PROMPT = """你是一个软件工程助手。请完成下面的任务。

任务：{task_description}
工作目录：{workspace}

请只修改完成任务所需的文件，执行必要验证，完成后给出简短结果说明。
"""

CEL_TREATMENT = """
本次实验启用“收敛式工程迭代”技能。请加载
convergent-engineering-loop，并遵循其协议完成任务。
"""

SOURCE_GUARD_TARGETS = (
    CEL_SOURCE,
    CEL_EVAL_SKILL_SOURCE,
    ROOT / "harness",
    ROOT / "evaluators",
    ROOT / "base",
    ROOT / "tasks",
    ROOT / "task_suite.json",
    ROOT / "_runner.py",
)

TREATMENT_SKILL_LOCATIONS = (
    Path(".agents/skills/convergent-engineering-loop"),
    Path(".codebuddy/skills/convergent-engineering-loop"),
    Path(".codex/skills/convergent-engineering-loop"),
    Path(".claude/skills/convergent-engineering-loop"),
)


def run_pytest(work_dir: Path, output_file: Path):
    """运行 pytest 并保存结果。"""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--tb=short",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(work_dir),
        capture_output=True,
        text=True,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    txt = result.stdout + "\n" + result.stderr
    output_file.write_text(txt, encoding="utf-8")
    return txt


def file_list(work_dir: Path, output_file: Path):
    """记录文件列表。"""
    files = []
    for f in sorted(work_dir.rglob("*")):
        if f.is_file() and "__pycache__" not in str(f) and ".pyc" not in f.suffix:
            files.append(str(f.relative_to(work_dir)))
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(files), encoding="utf-8")


def diff_dirs(a_dir: Path, b_dir: Path, output_file: Path):
    """对比两个目录的差异。"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    # 用 Python diff
    a_files = set()
    b_files = set()
    for f in a_dir.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f) and ".pyc" not in f.suffix:
            a_files.add(str(f.relative_to(a_dir)))
    for f in b_dir.rglob("*"):
        if f.is_file() and "__pycache__" not in str(f) and ".pyc" not in f.suffix:
            b_files.add(str(f.relative_to(b_dir)))
    added = b_files - a_files
    removed = a_files - b_files
    common = a_files & b_files
    changed = []
    for f in sorted(common):
        a_path = a_dir / f
        b_path = b_dir / f
        if a_path.read_bytes() != b_path.read_bytes():
            a_text = a_path.read_text(errors="replace")
            b_text = b_path.read_text(errors="replace")
            a_lines = a_text.count("\n")
            b_lines = b_text.count("\n")
            changed.append(f"{f}: {a_lines}→{b_lines} lines")
    lines = []
    if added:
        lines.append(f"--- Added files ({len(added)}) ---")
        for f in sorted(added):
            lines.append(f"  + {f}")
    if removed:
        lines.append(f"--- Removed files ({len(removed)}) ---")
        for f in sorted(removed):
            lines.append(f"  - {f}")
    if changed:
        lines.append(f"--- Changed files ({len(changed)}) ---")
        for c in changed:
            lines.append(f"  ~ {c}")
    if not lines:
        lines.append("No differences found.")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")


def parse_pytest(txt: str):
    """从 pytest 输出中提取通过/失败数量。"""
    passed = 0
    failed = 0
    for line in txt.split("\n"):
        if "passed" in line:
            # e.g. "52 passed in 0.31s"
            import re

            m = re.search(r"(\d+)\s+passed", line)
            if m:
                passed = int(m.group(1))
            m = re.search(r"(\d+)\s+failed", line)
            if m:
                failed = int(m.group(1))
    return passed, failed


def _copy_task_workspace(task_id: str, target: Path):
    """把全绿基线和任务 overlay 复制到一个全新的目录。"""
    if target.exists():
        raise FileExistsError(f"拒绝复用已有工作区: {target}")
    shutil.copytree(BASE, target)
    init_dir = TASKS / task_id / "init"
    if init_dir.exists():
        for item in init_dir.iterdir():
            dest = target / item.relative_to(init_dir)
            if item.is_dir():
                # Task fixtures are overlays. Replacing an existing top-level
                # directory discards unrelated base files and tests.
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)


def prepare_workspace(task_id: str, target: Path):
    """兼容入口：只允许在评测项目内部创建一个全新的显式工作区。"""
    target = target.resolve()
    if ROOT not in target.parents or target in {BASE.resolve(), TASKS.resolve()}:
        raise ValueError(f"workspace target must be a child of {ROOT}: {target}")
    _copy_task_workspace(task_id, target)


def init_snapshot(work_dir: Path, task_id: str, group: str):
    """记录初始快照。"""
    out_dir = OUTPUT / task_id / group
    out_dir.mkdir(parents=True, exist_ok=True)
    pytest_txt = run_pytest(work_dir, out_dir / "init_tests.txt")
    passed, failed = parse_pytest(pytest_txt)
    file_list(work_dir, out_dir / "init_files.txt")
    return passed, failed


def collect_metrics(work_dir: Path, task_id: str, group: str):
    """采集指标。"""
    out_dir = OUTPUT / task_id / group
    out_dir.mkdir(parents=True, exist_ok=True)
    pytest_txt = run_pytest(work_dir, out_dir / "metrics_tests.txt")
    passed, failed = parse_pytest(pytest_txt)
    diff_dirs(BASE, work_dir, out_dir / "diff.txt")
    # 写入简单指标
    metrics = {"passed": passed, "failed": failed, "total": passed + failed}
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    return metrics


def load_suite_manifest() -> dict:
    """读取唯一的活动任务清单。run_config.yaml 不再决定默认任务。"""
    return json.loads(SUITE_MANIFEST.read_text(encoding="utf-8"))


def list_suite(suite_name: str | None = None) -> list[dict]:
    manifest = load_suite_manifest()
    suite_name = suite_name or manifest["default_suite"]
    if suite_name not in manifest["suites"]:
        raise KeyError(f"unknown suite: {suite_name}")
    tasks = []
    for task_id in manifest["suites"][suite_name]["tasks"]:
        metadata = manifest.get("tasks", {}).get(task_id, {})
        tasks.append({"id": task_id, **metadata})
    return tasks


def _ruff_targets(task: dict, workspace: Path) -> list[str]:
    targets = []
    for pattern in task.get("allowed_paths", []):
        if any(char in pattern for char in "*?[") or not pattern.endswith(".py"):
            continue
        if (workspace / pattern).exists():
            targets.append(pattern)
    return targets


def build_collector_config(
    task_id: str,
    group: str,
    platform: str,
    workspace: Path,
    output: Path,
    *,
    batch_id: str | None = None,
    batch_root: Path | None = None,
    source_guard: Path | None = None,
    cel_runtime: dict | None = None,
) -> Path:
    manifest = load_suite_manifest()
    task = manifest.get("tasks", {}).get(task_id)
    if task is None:
        raise KeyError(
            f"task {task_id} has no executable metadata in {SUITE_MANIFEST.name}"
        )
    workspace = workspace.resolve()
    output = output.resolve()
    validators = [
        {
            "name": "pytest",
            "parser": "pytest",
            "argv": [
                sys.executable,
                "-m",
                "pytest",
                "--tb=short",
                "-q",
                "--no-header",
                "-p",
                "no:cacheprovider",
            ],
            "timeout_seconds": 300,
        }
    ]
    ruff_targets = _ruff_targets(task, workspace)
    if ruff_targets:
        validators.append(
            {
                "name": "ruff",
                "parser": "ruff",
                "argv": [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    *ruff_targets,
                    "--no-cache",
                    "--output-format",
                    "concise",
                ],
                "timeout_seconds": 120,
            }
        )
    if task_id in {"T05", "T10", "T14", "T17", "T19", "T20"}:
        validators.append(
            {
                "name": "acceptance",
                "parser": "pytest",
                "argv": [
                    sys.executable,
                    str((ROOT / "evaluators" / "task_acceptance.py").resolve()),
                    task_id,
                    "{workspace}",
                ],
                "timeout_seconds": 120,
            }
        )
    config = {
        "schema_version": 1,
        "task_id": task_id,
        "group": group,
        "platform": platform,
        "workspace": str(workspace),
        "output": str(output),
        "allowed_paths": task["allowed_paths"],
        "validation_commands": validators,
        "validation_mode": "isolated_copy",
    }
    if batch_id is not None:
        config["batch_id"] = batch_id
    if batch_root is not None:
        config["batch_root"] = str(batch_root.resolve())
    if source_guard is not None:
        config["source_guard"] = str(source_guard.resolve())
    if cel_runtime is not None:
        config["cel_runtime"] = cel_runtime
    output.mkdir(parents=True, exist_ok=True)
    config_path = output / "collector-config.json"
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    verify_config_isolation(config)
    return config_path


def _manifest_digest(manifest: dict) -> str:
    payload = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_batch_id(batch_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", batch_id):
        raise ValueError(
            "batch_id 只能包含字母、数字、点、下划线和连字符，且不能包含路径"
        )
    return batch_id


def _install_cel_runtime(workspace: Path, platform: str) -> dict:
    """安装一次性 CEL 副本；不把真源目录交给 worker 修改。"""
    if platform == "codex":
        destination = (
            workspace / ".agents" / "skills" / "convergent-engineering-loop"
        )
    elif platform == "codebuddy":
        destination = (
            workspace / ".codebuddy" / "skills" / "convergent-engineering-loop"
        )
    else:
        raise ValueError(f"不支持的平台: {platform}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CEL_SOURCE, destination)
    return {"path": str(destination.resolve()), "sha256": path_digest(destination)}


def _assert_no_parent_treatment_skill(batch_root: Path) -> None:
    """拒绝可能被 Control 沿父目录发现的仓库级 CEL 安装。"""
    leaked = []
    for parent in (batch_root, *batch_root.parents):
        for relative in TREATMENT_SKILL_LOCATIONS:
            candidate = parent / relative
            if candidate.exists():
                leaked.append(str(candidate.resolve()))
    if leaked:
        raise RuntimeError(
            "Control 的父目录中发现 convergent-engineering-loop，无法保证无 CEL: "
            + ", ".join(sorted(set(leaked)))
        )


def _initialize_workspace_repo(workspace: Path) -> Path:
    """建立独立 Git 根和空用户目录，截断父仓库与用户级 skill 发现。"""
    worker_home = workspace / ".eval-user-home"
    worker_home.mkdir()
    commands = (
        ["git", "init", "--quiet"],
        ["git", "add", "-A"],
        [
            "git",
            "-c",
            "user.name=CEL Evaluation",
            "-c",
            "user.email=cel-eval@invalid.local",
            "commit",
            "--quiet",
            "-m",
            "evaluation baseline",
        ],
    )
    for command in commands:
        subprocess.run(
            command,
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    return worker_home.resolve()


def _render_prompt(task: dict, group: str, workspace: Path) -> str:
    prompt = COMMON_PROMPT.format(
        task_description=task["description"], workspace=workspace.resolve()
    )
    if group == "cel":
        prompt += CEL_TREATMENT
    elif group != "control":
        raise ValueError(f"不支持的实验组: {group}")
    return prompt


def create_batch(
    batch_id: str,
    platform: str,
    suite_name: str = "primary",
    runs_root: Path = RUNS_ROOT,
) -> Path:
    """一次性创建批次、Control/CEL 独立工作区、配置和提示词。"""
    batch_id = _validate_batch_id(batch_id)
    platform = platform.lower()
    if platform not in {"codex", "codebuddy"}:
        raise ValueError("platform 必须是 codex 或 codebuddy")
    batch_root = (runs_root.resolve() / batch_id).resolve()
    _assert_no_parent_treatment_skill(batch_root)
    if batch_root.exists():
        raise FileExistsError(f"拒绝复用已有批次目录: {batch_root}")
    batch_root.mkdir(parents=True)

    source_guard_path = batch_root / "source-guard.json"
    write_source_guard(
        source_guard_path, SOURCE_GUARD_TARGETS, anchor=PROJECT_ROOT
    )
    entries = []
    try:
        for task in list_suite(suite_name):
            task_id = task["id"]
            pair_payloads = {}
            pair_entries = []
            for group in ("control", "cel"):
                workspace = batch_root / "workspaces" / task_id / group
                output = batch_root / "results" / task_id / group
                _copy_task_workspace(task_id, workspace)
                payload_manifest = workspace_manifest(workspace)
                pair_payloads[group] = _manifest_digest(payload_manifest)
                cel_runtime = (
                    _install_cel_runtime(workspace, platform)
                    if group == "cel"
                    else None
                )
                worker_home = _initialize_workspace_repo(workspace)
                config_path = build_collector_config(
                    task_id,
                    group,
                    platform,
                    workspace,
                    output,
                    batch_id=batch_id,
                    batch_root=batch_root,
                    source_guard=source_guard_path,
                    cel_runtime=cel_runtime,
                )
                config = json.loads(config_path.read_text(encoding="utf-8"))
                config["worker_home"] = str(worker_home)
                config_path.write_text(
                    json.dumps(config, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                prompt_path = output / "prompt.txt"
                prompt_path.write_text(
                    _render_prompt(task, group, workspace), encoding="utf-8"
                )
                pair_entries.append(
                    {
                        "group": group,
                        "workspace": str(workspace.resolve()),
                        "output": str(output.resolve()),
                        "config": str(config_path.resolve()),
                        "prompt": str(prompt_path.resolve()),
                        "initial_payload_sha256": pair_payloads[group],
                        "cel_runtime": cel_runtime,
                    }
                )
            if pair_payloads["control"] != pair_payloads["cel"]:
                raise RuntimeError(f"{task_id} 的 Control/CEL 初始任务载荷不一致")
            entries.append(
                {
                    "task_id": task_id,
                    "initial_pair_equal": True,
                    "runs": pair_entries,
                }
            )
    except Exception:
        shutil.rmtree(batch_root, ignore_errors=True)
        raise

    manifest = {
        "schema_version": 1,
        "batch_id": batch_id,
        "platform": platform,
        "suite": suite_name,
        "batch_root": str(batch_root),
        "source_guard": str(source_guard_path.resolve()),
        "tasks": entries,
    }
    manifest_path = batch_root / "batch-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest_path


def verify_batch(batch_root: Path) -> dict:
    """验证批次边界、CEL 真源和运行时副本完整性。"""
    batch_root = batch_root.resolve()
    manifest_path = batch_root / "batch-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_result = verify_source_guard(Path(manifest["source_guard"]))
    runs = []
    for task in manifest["tasks"]:
        for run in task["runs"]:
            config = json.loads(Path(run["config"]).read_text(encoding="utf-8"))
            runs.append(
                {
                    "task_id": task["task_id"],
                    "group": run["group"],
                    **verify_config_isolation(config),
                }
            )
    report = {
        "schema_version": 1,
        "ok": True,
        "batch_id": manifest["batch_id"],
        "source_guard": source_result,
        "all_initial_pairs_equal": all(
            task["initial_pair_equal"] for task in manifest["tasks"]
        ),
        "runs": runs,
    }
    (batch_root / "isolation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "help"
    task_id = sys.argv[2] if len(sys.argv) > 2 else ""
    group = sys.argv[3] if len(sys.argv) > 3 else ""

    if action == "list":
        suite = sys.argv[2] if len(sys.argv) > 2 else None
        for task in list_suite(suite):
            print(
                f"{task['id']}\t{task.get('complexity', '-')}\t"
                f"{task.get('domain', '-')}\t{task.get('axis', '-')}"
            )

    elif action == "prepare":
        if len(sys.argv) < 4:
            raise ValueError("prepare 必须显式提供唯一工作区: prepare TASK TARGET")
        target = Path(sys.argv[3])
        prepare_workspace(task_id, target)
        print(f"OK: prepared {task_id} at {target}")

    elif action == "config":
        # python _runner.py config T18 cel codex <absolute-output> [workspace]
        platform = sys.argv[4] if len(sys.argv) > 4 else "codex"
        output = Path(sys.argv[5]) if len(sys.argv) > 5 else OUTPUT / task_id / group
        workspace = Path(sys.argv[6]) if len(sys.argv) > 6 else RUNNER_WORKING
        config_path = build_collector_config(
            task_id, group, platform, workspace, output
        )
        print(config_path)

    elif action == "init_snapshot":
        target = RUNNER_WORKING
        passed, failed = init_snapshot(target, task_id, group)
        print(f"OK: init snapshot {passed} passed, {failed} failed")

    elif action == "collect":
        target = RUNNER_WORKING
        metrics = collect_metrics(target, task_id, group)
        print(f"OK: collected metrics - {metrics}")

    elif action == "batch":
        if len(sys.argv) < 4:
            raise ValueError(
                "用法: batch BATCH_ID PLATFORM [SUITE] [RUNS_ROOT]"
            )
        batch_id = sys.argv[2]
        platform = sys.argv[3]
        suite = sys.argv[4] if len(sys.argv) > 4 else "primary"
        runs_root = Path(sys.argv[5]) if len(sys.argv) > 5 else RUNS_ROOT
        print(create_batch(batch_id, platform, suite, runs_root))

    elif action == "verify_batch":
        if len(sys.argv) < 3:
            raise ValueError("用法: verify_batch BATCH_ROOT")
        print(
            json.dumps(
                verify_batch(Path(sys.argv[2])), ensure_ascii=False, indent=2
            )
        )

    elif action == "help":
        print(
            "操作:\n"
            "  list [SUITE]\n"
            "  batch BATCH_ID PLATFORM [SUITE] [RUNS_ROOT]\n"
            "  verify_batch BATCH_ROOT\n"
            "  prepare TASK TARGET（兼容入口，必须显式指定唯一目录）\n"
            "  config TASK GROUP PLATFORM OUTPUT [WORKSPACE]"
        )
