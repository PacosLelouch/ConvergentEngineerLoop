"""Run ``codex exec --json`` with mutation-aware metric checkpoints."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .isolation import verify_config_isolation
from .metrics import reduce_metrics
from .snapshot import capture_checkpoint, load_config


def _toml_string(value: str) -> str:
    # JSON basic strings are valid TOML basic strings for these command values.
    return json.dumps(value)


def _hook_override(command: str) -> str:
    encoded = _toml_string(command)
    return (
        'hooks.PostToolUse=[{matcher="*",hooks=[{type="command",'
        f"command={encoded},command_windows={encoded},timeout=300}}]}}]"
    )


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def _read_stderr(stream: Any, target: Path) -> None:
    with target.open("w", encoding="utf-8", newline="\n") as output:
        for line in stream:
            output.write(line)
            output.flush()


def _merge_usage(total: dict[str, int], usage: dict[str, Any]) -> None:
    for key in (
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    ):
        total[key] = total.get(key, 0) + int(usage.get(key, 0) or 0)


def _resolve_codex(config: dict[str, Any]) -> str:
    explicit = config.get("codex_executable")
    if explicit:
        return str(explicit)
    if os.name == "nt":
        npm_wrapper = shutil.which("codex.cmd")
        if npm_wrapper:
            package_root = (
                Path(npm_wrapper).parent / "node_modules" / "@openai" / "codex"
            )
            candidates = sorted(
                package_root.glob(
                    "node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe"
                )
            )
            if candidates:
                return str(candidates[0])
        native = shutil.which("codex.exe")
        if native:
            return native
    return shutil.which("codex") or "codex"


def run(config_path: Path, prompt: str) -> int:
    config_path = config_path.resolve()
    config = load_config(config_path)
    verify_config_isolation(config)
    workspace = Path(config["workspace"])
    output = Path(config["output"])
    output.mkdir(parents=True, exist_ok=True)
    if (output / "checkpoints.jsonl").exists():
        raise FileExistsError(f"refusing to append to existing run: {output}")

    capture_checkpoint(config, "baseline", {"event": "runner_baseline"})
    project_root = Path(__file__).resolve().parent.parent
    hook_command = f'"{sys.executable}" -m harness.hook'
    command = [
        _resolve_codex(config),
        "exec",
        "--json",
        "--sandbox",
        "workspace-write",
        "--ignore-user-config",
        "-C",
        str(workspace),
        "--dangerously-bypass-hook-trust",
        "-c",
        "features.hooks=true",
        "-c",
        _hook_override(hook_command),
    ]
    command.extend(str(value) for value in config.get("codex_args", []))
    command.append("-")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(project_root) + (
        os.pathsep + existing_pythonpath if existing_pythonpath else ""
    )
    env["CEL_METRICS_CONFIG"] = str(config_path)
    worker_home = Path(config.get("worker_home", workspace / ".eval-user-home"))
    worker_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(worker_home)
    if os.name == "nt":
        env["USERPROFILE"] = str(worker_home)
        env["HOMEDRIVE"] = worker_home.drive
        env["HOMEPATH"] = str(worker_home)[len(worker_home.drive) :]

    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=str(workspace),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        shell=False,
    )
    assert process.stdin and process.stdout and process.stderr
    process.stdin.write(prompt)
    process.stdin.close()
    stderr_thread = threading.Thread(
        target=_read_stderr,
        args=(process.stderr, output / "platform-stderr.txt"),
        daemon=True,
    )
    stderr_thread.start()

    usage: dict[str, int] = {}
    turns = 0
    raw_path = output / "platform-events.jsonl"
    normalized_path = output / "events.jsonl"
    for line in process.stdout:
        with raw_path.open("a", encoding="utf-8", newline="\n") as raw:
            raw.write(line)
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "turn.started":
            turns += 1
        elif event_type == "turn.completed":
            _merge_usage(usage, event.get("usage", {}))
        item = event.get("item", {})
        item_type = item.get("type")
        if item_type == "file_change":
            paths = [
                change.get("path")
                for change in item.get("changes", [])
                if change.get("path")
            ]
            _append_jsonl(normalized_path, {"event": "file_change", "paths": paths})
        elif item_type == "command_execution":
            _append_jsonl(
                normalized_path,
                {
                    "event": "command_execution",
                    "command": item.get("command"),
                    "status": item.get("status"),
                },
            )

    returncode = process.wait()
    stderr_thread.join(timeout=5)
    capture_checkpoint(config, "final", {"event": "runner_final"})
    run_data = {
        "platform": "codex",
        "exit_code": returncode,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "num_turns": turns,
        "usage": usage,
        "command": command[:-1] + ["<prompt-from-stdin>"],
    }
    (output / "run.json").write_text(
        json.dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    verify_config_isolation(config)
    reduce_metrics(config)
    return returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file", type=Path)
    args = parser.parse_args()
    prompt = (
        args.prompt
        if args.prompt is not None
        else args.prompt_file.read_text(encoding="utf-8")
    )
    return run(args.config, prompt)


if __name__ == "__main__":
    raise SystemExit(main())
