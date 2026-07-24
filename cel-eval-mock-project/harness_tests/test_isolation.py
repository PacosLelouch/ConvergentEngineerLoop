from __future__ import annotations

import json
from pathlib import Path

import _runner as runner
import pytest


def test_batch_has_independent_control_and_cel_workspaces(
    tmp_path: Path, monkeypatch
) -> None:
    task = runner.load_suite_manifest()["tasks"]["T04"]
    monkeypatch.setattr(
        runner, "list_suite", lambda _suite: [{"id": "T04", **task}]
    )

    manifest_path = runner.create_batch(
        "batch-test", "codex", "primary", tmp_path / "runs"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    task_entry = manifest["tasks"][0]
    control = task_entry["runs"][0]
    cel = task_entry["runs"][1]
    control_workspace = Path(control["workspace"])
    cel_workspace = Path(cel["workspace"])

    assert task_entry["initial_pair_equal"] is True
    assert control["initial_payload_sha256"] == cel["initial_payload_sha256"]
    assert control_workspace != cel_workspace
    assert not (
        control_workspace
        / ".agents"
        / "skills"
        / "convergent-engineering-loop"
    ).exists()
    assert (
        cel_workspace / ".agents" / "skills" / "convergent-engineering-loop"
    ).is_dir()
    assert (control_workspace / ".git").is_dir()
    assert (cel_workspace / ".git").is_dir()
    assert (control_workspace / ".eval-user-home").is_dir()
    assert (cel_workspace / ".eval-user-home").is_dir()
    assert (
        json.loads(Path(control["config"]).read_text(encoding="utf-8"))[
            "worker_home"
        ]
        == str((control_workspace / ".eval-user-home").resolve())
    )

    cel_target = cel_workspace / "src" / "data_processor.py"
    control_before = (
        control_workspace / "src" / "data_processor.py"
    ).read_bytes()
    cel_target.write_text("# cel-only mutation\n", encoding="utf-8")
    assert (
        control_workspace / "src" / "data_processor.py"
    ).read_bytes() == control_before

    report = runner.verify_batch(manifest_path.parent)
    assert report["ok"] is True
    assert report["all_initial_pairs_equal"] is True


def test_control_prompt_has_no_negative_cel_intervention(tmp_path: Path) -> None:
    task = {"description": "修复一个函数。"}
    control = runner._render_prompt(task, "control", tmp_path / "control")
    cel = runner._render_prompt(task, "cel", tmp_path / "cel")

    assert "收敛式工程迭代" not in control
    assert "不要遵循" not in control
    assert "convergent-engineering-loop" not in control
    assert "收敛式工程迭代" in cel
    assert "convergent-engineering-loop" in cel


def test_batch_rejects_parent_treatment_skill(
    tmp_path: Path, monkeypatch
) -> None:
    task = runner.load_suite_manifest()["tasks"]["T04"]
    monkeypatch.setattr(
        runner, "list_suite", lambda _suite: [{"id": "T04", **task}]
    )
    leaked = (
        tmp_path
        / "repo"
        / ".agents"
        / "skills"
        / "convergent-engineering-loop"
    )
    leaked.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="无法保证无 CEL"):
        runner.create_batch(
            "batch-test",
            "codex",
            "primary",
            tmp_path / "repo" / "test-runs",
        )
