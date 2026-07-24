from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from harness.metrics import reduce_metrics
from harness.snapshot import capture_checkpoint


def _config(workspace: Path, output: Path) -> dict:
    score_script = (
        "from pathlib import Path; "
        "n=int(Path('src/demo.py').read_text()); "
        "print(f'{5-n} passed, {n} failed')"
    )
    return {
        "task_id": "TEST",
        "platform": "fixture",
        "workspace": str(workspace),
        "output": str(output),
        "allowed_paths": ["src/**"],
        "validation_commands": [
            {
                "name": "pytest",
                "parser": "pytest",
                "argv": [sys.executable, "-c", score_script],
            }
        ],
    }


def test_content_changes_create_checkpoints_and_reduce_metrics(tmp_path: Path) -> None:
    workspace = tmp_path / "working"
    output = tmp_path / "result"
    (workspace / "src").mkdir(parents=True)
    source = workspace / "src" / "demo.py"
    source.write_text("3", encoding="utf-8")
    config = _config(workspace, output)

    baseline = capture_checkpoint(config, "baseline")
    assert baseline and baseline["error_score"] == 3
    assert (
        capture_checkpoint(config, "post_tool_use", {"tool_name": "read_file"}) is None
    )

    source.write_text("2", encoding="utf-8")
    capture_checkpoint(config, "post_tool_use", {"tool_name": "apply_patch"})
    source.write_text("3", encoding="utf-8")
    capture_checkpoint(config, "post_tool_use", {"tool_name": "apply_patch"})
    source.write_text("0", encoding="utf-8")
    (workspace / "README.md").write_text("out of scope", encoding="utf-8")
    capture_checkpoint(config, "post_tool_use", {"tool_name": "apply_patch"})

    (output / "run.json").write_text(
        json.dumps(
            {
                "platform": "fixture",
                "usage": {"input_tokens": 11, "output_tokens": 7},
            }
        ),
        encoding="utf-8",
    )
    metrics = reduce_metrics(config)

    assert metrics["error_sequence"] == [3, 2, 3, 0]
    assert metrics["CNV-3"]["effective_round_rate"] == pytest.approx(2 / 3, abs=1e-6)
    assert metrics["CNV-4"]["total_tokens"] == 18
    assert metrics["OSC-1"]["locations"] == ["src/demo.py"]
    assert metrics["EXP-1"]["drift_files"] == ["README.md"]
    assert metrics["terminal"]["success"] is True


def test_validator_output_and_hook_metadata_are_external(tmp_path: Path) -> None:
    workspace = tmp_path / "working"
    output = tmp_path / "result"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "demo.py").write_text("1", encoding="utf-8")
    config = _config(workspace, output)

    record = capture_checkpoint(
        config,
        "baseline",
        {"tool_name": "Bash", "tool_input": {"command": "secret", "description": "x"}},
    )

    assert record is not None
    assert record["event"]["tool_name"] == "Bash"
    assert record["event"]["input_keys"] == ["command", "description"]
    assert "secret" not in (output / "checkpoints.jsonl").read_text(encoding="utf-8")
    assert not (workspace / "checkpoints.jsonl").exists()
    assert (output / "checkpoints" / "0000" / "pytest.txt").exists()


def test_validator_runs_in_disposable_copy(tmp_path: Path) -> None:
    workspace = tmp_path / "working"
    output = tmp_path / "result"
    workspace.mkdir()
    (workspace / "state.txt").write_text("agent-state", encoding="utf-8")
    config = {
        "task_id": "TEST",
        "platform": "fixture",
        "workspace": str(workspace),
        "output": str(output),
        "allowed_paths": ["state.txt"],
        "validation_commands": [
            {
                "name": "mutating-validator",
                "parser": "exit_code",
                "argv": [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; "
                        "Path('state.txt').write_text('validator-state'); "
                        "Path('validator.tmp').write_text('created')"
                    ),
                ],
            }
        ],
    }

    record = capture_checkpoint(config, "baseline")

    assert record is not None
    assert record["validation_isolated"] is True
    assert (workspace / "state.txt").read_text(encoding="utf-8") == "agent-state"
    assert not (workspace / "validator.tmp").exists()
    assert list((output / ".validation-sandboxes").iterdir()) == []
