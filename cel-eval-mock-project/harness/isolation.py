"""实验运行边界与 CEL 真源完整性守卫。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def path_digest(path: Path) -> str:
    """计算文件或目录的稳定内容摘要，不包含缓存和版本库元数据。"""
    path = path.resolve()
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    ignored_dirs = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
    }
    ignored_suffixes = {".pyc", ".pyo"}
    for item in sorted(path.rglob("*"), key=lambda value: value.as_posix()):
        relative = item.relative_to(path)
        if any(part in ignored_dirs for part in relative.parts):
            continue
        if not item.is_file() or item.suffix in ignored_suffixes:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_source_guard(
    guard_path: Path, sources: Iterable[Path], *, anchor: Path
) -> dict[str, Any]:
    """记录实验开始前不可变真源的摘要。"""
    anchor = anchor.resolve()
    records = []
    for source in sources:
        source = source.resolve()
        try:
            label = source.relative_to(anchor).as_posix()
        except ValueError:
            label = str(source)
        records.append(
            {
                "label": label,
                "path": str(source),
                "sha256": path_digest(source),
            }
        )
    guard = {"schema_version": 1, "sources": records}
    guard_path.parent.mkdir(parents=True, exist_ok=True)
    guard_path.write_text(
        json.dumps(guard, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return guard


def verify_source_guard(guard_path: Path) -> dict[str, Any]:
    """验证 CEL、harness、任务模板等真源未在运行中被修改。"""
    guard_path = guard_path.resolve()
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    changed = []
    missing = []
    for record in guard.get("sources", []):
        path = Path(record["path"])
        if not path.exists():
            missing.append(record["label"])
            continue
        actual = path_digest(path)
        if actual != record["sha256"]:
            changed.append(
                {
                    "label": record["label"],
                    "expected": record["sha256"],
                    "actual": actual,
                }
            )
    result = {
        "ok": not changed and not missing,
        "changed": changed,
        "missing": missing,
    }
    if not result["ok"]:
        raise RuntimeError(f"实验真源完整性检查失败: {result}")
    return result


def verify_config_isolation(config: dict[str, Any]) -> dict[str, Any]:
    """检查单次运行的工作区、观察结果和批次边界。"""
    workspace = Path(config["workspace"]).resolve()
    output = Path(config["output"]).resolve()
    if not workspace.is_dir():
        raise FileNotFoundError(f"工作区不存在: {workspace}")
    if config.get("batch_id") and not (workspace / ".git").is_dir():
        raise ValueError("批次工作区必须是独立 Git 根")
    if workspace == output or _is_within(output, workspace) or _is_within(
        workspace, output
    ):
        raise ValueError("workspace 与 output 必须是互不包含的兄弟目录")

    batch_root_value = config.get("batch_root")
    if batch_root_value:
        batch_root = Path(batch_root_value).resolve()
        if not _is_within(workspace, batch_root) or not _is_within(
            output, batch_root
        ):
            raise ValueError("workspace/output 必须位于声明的 batch_root 内")

    worker_home_value = config.get("worker_home")
    if worker_home_value:
        worker_home = Path(worker_home_value).resolve()
        if not _is_within(worker_home, workspace):
            raise ValueError("worker_home 必须位于当前独立工作区中")

    group = config.get("group")
    local_treatment_paths = (
        workspace / ".agents" / "skills" / "convergent-engineering-loop",
        workspace / ".codebuddy" / "skills" / "convergent-engineering-loop",
        workspace / ".codex" / "skills" / "convergent-engineering-loop",
        workspace / ".claude" / "skills" / "convergent-engineering-loop",
    )
    if group == "control" and any(path.exists() for path in local_treatment_paths):
        raise RuntimeError("Control 工作区中不得存在 CEL treatment skill")
    if group == "cel" and not any(path.exists() for path in local_treatment_paths):
        raise RuntimeError("CEL 工作区缺少平台专用 treatment skill")

    guard_result = None
    if config.get("source_guard"):
        guard_result = verify_source_guard(Path(config["source_guard"]))

    runtime_result = None
    runtime = config.get("cel_runtime")
    if runtime:
        runtime_path = Path(runtime["path"]).resolve()
        actual = path_digest(runtime_path)
        runtime_result = {
            "ok": actual == runtime["sha256"],
            "path": str(runtime_path),
            "expected": runtime["sha256"],
            "actual": actual,
        }
        if not runtime_result["ok"]:
            raise RuntimeError("本次运行使用的 CEL 安装副本被修改")

    return {
        "ok": True,
        "workspace": str(workspace),
        "output": str(output),
        "source_guard": guard_result,
        "cel_runtime": runtime_result,
    }
