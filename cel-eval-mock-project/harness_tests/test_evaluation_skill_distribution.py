from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import sync_evaluation_skill


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SYNC_PLATFORMS = REPOSITORY_ROOT / "scripts" / "sync-platforms.py"


def _run_product_sync(*arguments: str) -> None:
    subprocess.run(
        [sys.executable, str(SYNC_PLATFORMS), *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )


def _assert_no_evaluation_skill(root: Path) -> None:
    leaked = [
        path
        for path in root.rglob("*")
        if "cel-ab-evaluation" in path.name.lower()
    ]
    assert leaked == []


@pytest.mark.parametrize("package_format", ["folders", "plugins"])
def test_product_packages_exclude_evaluation_skill(
    tmp_path: Path, package_format: str
) -> None:
    output = tmp_path / package_format
    _run_product_sync(
        "--format",
        package_format,
        "--output",
        str(output),
    )

    _assert_no_evaluation_skill(output)


@pytest.mark.parametrize(
    ("platform", "treatment_path", "evaluation_path"),
    [
        (
            "codex",
            Path(".agents/skills/convergent-engineering-loop"),
            Path(".agents/skills/cel-ab-evaluation"),
        ),
        (
            "codebuddy",
            Path(".codebuddy/skills/convergent-engineering-loop"),
            Path(".codebuddy/skills/cel-ab-evaluation"),
        ),
    ],
)
def test_product_install_excludes_and_cleans_legacy_evaluation_skill(
    tmp_path: Path,
    platform: str,
    treatment_path: Path,
    evaluation_path: Path,
) -> None:
    project = tmp_path / platform
    legacy_evaluation = project / evaluation_path
    legacy_evaluation.mkdir(parents=True)
    (legacy_evaluation / "SKILL.md").write_text("legacy", encoding="utf-8")

    _run_product_sync(
        "--install",
        str(project),
        "--platform",
        platform,
    )

    assert (project / treatment_path).is_dir()
    assert not legacy_evaluation.exists()


def test_repository_evaluation_skill_copies_match_test_source() -> None:
    targets = sync_evaluation_skill.verify_synced()

    assert targets == (
        REPOSITORY_ROOT / ".agents/skills/cel-ab-evaluation",
        REPOSITORY_ROOT / ".codebuddy/skills/cel-ab-evaluation",
    )


def test_evaluation_sync_only_writes_repository_discovery_copies(
    tmp_path: Path,
) -> None:
    (tmp_path / "cel-eval-mock-project").mkdir()
    (tmp_path / "cel-eval-mock-project/task_suite.json").write_text(
        "{}",
        encoding="utf-8",
    )

    targets = sync_evaluation_skill.sync(tmp_path)

    assert targets == tuple(
        tmp_path / relative
        for relative in sync_evaluation_skill.RELATIVE_TARGETS
    )
    assert not (
        tmp_path / ".agents/skills/convergent-engineering-loop"
    ).exists()
    assert not (
        tmp_path / ".codebuddy/skills/convergent-engineering-loop"
    ).exists()
