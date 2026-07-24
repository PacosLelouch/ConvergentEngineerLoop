from __future__ import annotations

from pathlib import Path

import yaml


EVALUATION_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EVALUATION_ROOT.parent


def test_run_document_is_owned_by_evaluation_project() -> None:
    config = yaml.safe_load(
        (EVALUATION_ROOT / "run_config.yaml").read_text(encoding="utf-8")
    )
    prompt_document = config["prompt_document"]
    document = (EVALUATION_ROOT / prompt_document["path"]).resolve()

    assert document == EVALUATION_ROOT / "README.md"
    content = document.read_text(encoding="utf-8")
    for required_heading in prompt_document["contains"]:
        assert required_heading in content

    assert not (
        REPOSITORY_ROOT / "meta_plan" / "test-run-prompts.md"
    ).exists()
    assert "cel-eval-mock-project/README.md" in (
        REPOSITORY_ROOT / "README.md"
    ).read_text(encoding="utf-8")
