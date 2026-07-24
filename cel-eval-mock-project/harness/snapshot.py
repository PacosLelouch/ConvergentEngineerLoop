"""Capture mutation checkpoints and run external validation commands.

The collector lives outside the agent workspace. A platform hook may call
``capture_checkpoint`` after every tool use; checkpoints are only created when
the workspace manifest changed, so read-only tools do not become fake rounds.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


IGNORED_DIRS = {
    ".agents",
    ".codebuddy",
    ".codex",
    ".eval-user-home",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}
IGNORED_FILES = {".coverage", "agent_log.txt"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_manifest(workspace: Path) -> dict[str, dict[str, Any]]:
    """Return stable hashes and sizes for meaningful workspace files."""
    manifest: dict[str, dict[str, Any]] = {}
    for root, dirnames, filenames in os.walk(workspace):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        root_path = Path(root)
        for filename in sorted(filenames):
            if filename in IGNORED_FILES or filename.endswith((".pyc", ".pyo")):
                continue
            path = root_path / filename
            try:
                data = path.read_bytes()
            except (OSError, PermissionError):
                continue
            rel = path.relative_to(workspace).as_posix()
            manifest[rel] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "lines": data.count(b"\n")
                + (1 if data and not data.endswith(b"\n") else 0),
            }
    return manifest


def _changed_paths(
    previous: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]
) -> list[str]:
    paths = set(previous) | set(current)
    return sorted(path for path in paths if previous.get(path) != current.get(path))


@contextmanager
def _file_lock(path: Path, timeout: float = 30.0) -> Iterator[None]:
    """Small cross-platform inter-process lock for synchronous platform hooks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    started = time.monotonic()
    while True:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except (OSError, BlockingIOError):
            if time.monotonic() - started > timeout:
                handle.close()
                raise TimeoutError(f"timed out acquiring metrics lock: {path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _parse_pytest(output: str) -> dict[str, Any]:
    counts = {name: 0 for name in ("passed", "failed", "errors", "skipped", "xfailed")}
    patterns = {
        "passed": r"(\d+)\s+passed",
        "failed": r"(\d+)\s+failed",
        "errors": r"(\d+)\s+errors?",
        "skipped": r"(\d+)\s+skipped",
        "xfailed": r"(\d+)\s+xfailed",
    }
    for name, pattern in patterns.items():
        matches = re.findall(pattern, output)
        if matches:
            counts[name] = int(matches[-1])
    counts["total"] = sum(counts.values())
    counts["error_score"] = counts["failed"] + counts["errors"]
    return counts


def _parse_ruff(output: str, returncode: int) -> dict[str, Any]:
    match = re.search(r"Found\s+(\d+)\s+errors?", output)
    if match:
        errors = int(match.group(1))
    elif "No module named ruff" in output or "not recognized" in output:
        return {"unavailable": True, "error_score": 0}
    else:
        errors = sum(
            1
            for line in output.splitlines()
            if re.match(r".+:\d+:\d+:\s+[A-Z]+\d+", line)
        )
        if returncode and not errors:
            errors = 1
    return {"errors": errors, "error_score": errors}


def _parse_mypy(output: str, returncode: int) -> dict[str, Any]:
    match = re.search(r"Found\s+(\d+)\s+errors?", output)
    if match:
        errors = int(match.group(1))
    elif "No module named mypy" in output or "not recognized" in output:
        return {"unavailable": True, "error_score": 0}
    else:
        errors = sum(1 for line in output.splitlines() if ": error:" in line)
        if returncode and not errors:
            errors = 1
    return {"errors": errors, "error_score": errors}


def _parse_validation(parser: str, output: str, returncode: int) -> dict[str, Any]:
    if parser == "pytest":
        result = _parse_pytest(output)
        if returncode not in (0, 1) and not result["error_score"]:
            result["infrastructure_error"] = True
        return result
    if parser == "ruff":
        return _parse_ruff(output, returncode)
    if parser == "mypy":
        return _parse_mypy(output, returncode)
    return {"error_score": 0 if returncode == 0 else 1}


def _remap_validator_argv(
    argv: list[str], source_workspace: Path, validation_workspace: Path
) -> list[str]:
    """把验证命令中指向 agent 工作区的参数重定向到只读观察副本。"""
    remapped: list[str] = []
    for value in argv:
        if value == "{workspace}":
            remapped.append(str(validation_workspace))
            continue
        candidate = Path(value)
        if candidate.is_absolute():
            try:
                relative = candidate.resolve().relative_to(source_workspace)
            except ValueError:
                pass
            else:
                remapped.append(str(validation_workspace / relative))
                continue
        remapped.append(value)
    return remapped


def run_validation(
    workspace: Path,
    output_dir: Path,
    spec: dict[str, Any],
    *,
    source_workspace: Path | None = None,
) -> dict[str, Any]:
    name = str(spec["name"])
    argv = [str(part) for part in spec["argv"]]
    if source_workspace is not None:
        argv = _remap_validator_argv(argv, source_workspace, workspace)
    timeout = float(spec.get("timeout_seconds", 300))
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in spec.get("env", {}).items()})
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            shell=False,
        )
        text = (
            completed.stdout
            + ("\n" if completed.stdout and completed.stderr else "")
            + completed.stderr
        )
        returncode = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode("utf-8", "replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", "replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        text = stdout + "\n" + stderr + f"\nTIMEOUT after {timeout:.1f}s"
        returncode = 124
        timed_out = True
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{name}.txt").write_text(text, encoding="utf-8")
    parsed = _parse_validation(str(spec.get("parser", "exit_code")), text, returncode)
    return {
        "name": name,
        "argv": argv,
        "returncode": returncode,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "timed_out": timed_out,
        **parsed,
    }


def _safe_event(event: dict[str, Any] | None) -> dict[str, Any]:
    """Keep structural event metadata without copying prompts or tool output."""
    event = event or {}
    tool_input = event.get("tool_input") or event.get("input") or {}
    return {
        "hook_event": event.get("hook_event_name")
        or event.get("hook_event")
        or event.get("event"),
        "tool_name": event.get("tool_name")
        or event.get("toolName")
        or event.get("name"),
        "tool_use_id": event.get("tool_use_id") or event.get("toolUseID"),
        "turn_id": event.get("turn_id"),
        "input_keys": sorted(tool_input) if isinstance(tool_input, dict) else [],
    }


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    config["workspace"] = str(Path(config["workspace"]).resolve())
    config["output"] = str(Path(config["output"]).resolve())
    return config


def _copy_for_validation(workspace: Path, parent: Path) -> Path:
    """创建一次性验证镜像，避免 pytest/lint 写回 agent 工作区。"""
    parent.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix="checkpoint-", dir=parent))
    shutil.rmtree(target)
    shutil.copytree(
        workspace,
        target,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            *sorted(IGNORED_DIRS),
            *sorted(IGNORED_FILES),
            "*.pyc",
            "*.pyo",
        ),
    )
    return target


def capture_checkpoint(
    config: dict[str, Any], cause: str, event: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Validate and persist one content-changing workspace checkpoint."""
    workspace = Path(config["workspace"]).resolve()
    output = Path(config["output"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / "collector-state.json"

    with _file_lock(output / "collector.lock"):
        state = (
            json.loads(state_path.read_text(encoding="utf-8"))
            if state_path.exists()
            else {}
        )
        previous = state.get("manifest", {})
        current = workspace_manifest(workspace)
        changed = _changed_paths(previous, current)
        is_baseline = cause == "baseline" or not state
        if not is_baseline and not changed:
            return None

        sequence = int(state.get("sequence", -1)) + 1
        checkpoint_dir = output / "checkpoints" / f"{sequence:04d}"
        validation_workspace = _copy_for_validation(
            workspace, output / ".validation-sandboxes"
        )
        try:
            validations = [
                run_validation(
                    validation_workspace,
                    checkpoint_dir,
                    spec,
                    source_workspace=workspace,
                )
                for spec in config.get("validation_commands", [])
            ]
        finally:
            shutil.rmtree(validation_workspace, ignore_errors=True)
        record = {
            "schema_version": 1,
            "sequence": sequence,
            "captured_at": _utc_now(),
            "cause": cause,
            "changed_paths": [] if is_baseline else changed,
            "changed_digests": {
                path: current.get(path) for path in ([] if is_baseline else changed)
            },
            "error_score": sum(int(item.get("error_score", 0)) for item in validations),
            "validation_isolated": True,
            "validations": validations,
            "event": _safe_event(event),
        }
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (checkpoint_dir / "checkpoint.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with (output / "checkpoints.jsonl").open(
            "a", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        if is_baseline:
            (output / "baseline-manifest.json").write_text(
                json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        state_path.write_text(
            json.dumps({"sequence": sequence, "manifest": current}, ensure_ascii=False),
            encoding="utf-8",
        )
        return record
