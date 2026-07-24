from __future__ import annotations

from generate_comparison import generate_objective_comparison
from harness.codex_runner import _hook_override


def _metrics(rounds: int, error: int, tokens: int) -> dict:
    return {
        "mutation_rounds": rounds,
        "CNV-2": {"convergence_instability": 0.0},
        "CNV-3": {"effective_round_rate": 0.5},
        "CNV-4": {"total_tokens": tokens},
        "EXP-1": {"scope_drift_rate": 0.0, "drift_files": []},
        "OSC-1": {"oscillated": False, "locations": []},
        "OSC-2": {"severity": 0.0},
        "DEC-2": {"validation_steps": 6},
        "terminal": {
            "initial_error": 3,
            "final_error": error,
            "success": error == 0,
            "initial_validations": [
                {"name": "pytest", "passed": 120, "failed": 3, "errors": 0}
            ],
            "final_validations": [
                {"name": "pytest", "passed": 123 - error, "failed": error, "errors": 0}
            ],
        },
    }


def test_comparison_prefers_objective_checkpoint_metrics() -> None:
    result = generate_objective_comparison(
        "T99",
        _metrics(rounds=4, error=1, tokens=100),
        _metrics(rounds=3, error=0, tokens=80),
    )

    assert result["terminal_metrics"]["success"]["delta"] == 1
    assert result["process_metrics"]["mutation_rounds"]["delta"] == -1
    assert result["process_metrics"]["CNV-4_total_tokens"]["delta"] == -20
    assert "agent_log" not in result["_data_sources"]


def test_codex_hook_override_is_a_toml_array() -> None:
    value = _hook_override('"C:\\Python\\python.exe" -m harness.hook')
    assert value.startswith("hooks.PostToolUse=[{")
    assert 'matcher="*"' in value
    assert "command_windows=" in value
