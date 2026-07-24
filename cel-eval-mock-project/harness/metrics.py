"""Reduce checkpoint and platform event streams to objective CEL metrics."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _allowed(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        pattern = pattern.replace("\\", "/")
        if pattern.endswith("/") and normalized.startswith(pattern):
            return True
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
    return False


def _platform_run(output: Path) -> dict[str, Any]:
    path = output / "run.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def reduce_metrics(config: dict[str, Any]) -> dict[str, Any]:
    output = Path(config["output"]).resolve()
    checkpoints = _read_jsonl(output / "checkpoints.jsonl")
    if not checkpoints:
        raise ValueError(f"no checkpoints found in {output}")

    errors = [int(row.get("error_score", 0)) for row in checkpoints]
    mutation_rows = [row for row in checkpoints if row.get("cause") != "baseline"]
    transitions = list(zip(errors, errors[1:]))
    decreased = sum(1 for before, after in transitions if after < before)
    increased = sum(1 for before, after in transitions if after > before)
    unchanged = sum(1 for before, after in transitions if after == before)

    final_error = errors[-1]
    first_final = next(
        index for index, value in enumerate(errors) if value == final_error
    )
    after_final = errors[first_final:]
    stability = 0.0
    if after_final:
        stability = 1.0 - (
            sum(value == final_error for value in after_final) / len(after_final)
        )

    baseline: dict[str, dict[str, Any]] = {}
    baseline_path = output / "baseline-manifest.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    histories: dict[str, list[str | None]] = {
        path: [value.get("sha256")] for path, value in baseline.items()
    }
    revision_counts: dict[str, int] = {}
    for row in mutation_rows:
        for path in row.get("changed_paths", []):
            revision_counts[path] = revision_counts.get(path, 0) + 1
            info = row.get("changed_digests", {}).get(path)
            histories.setdefault(path, [None]).append(
                info.get("sha256") if info else None
            )

    oscillating: list[str] = []
    for path, history in histories.items():
        revisions = revision_counts.get(path, 0)
        aba = any(
            history[index] in history[: index - 1] for index in range(2, len(history))
        )
        if revisions >= 3 or aba:
            oscillating.append(path)

    allowed_patterns = [str(item) for item in config.get("allowed_paths", [])]
    touched = sorted(revision_counts)
    drift = sorted(path for path in touched if not _allowed(path, allowed_patterns))
    total_revisions = sum(revision_counts.values())
    final_hashes = {path: history[-1] for path, history in histories.items()}
    overwritten = 0
    for path, history in histories.items():
        for digest in history[1:-1]:
            if digest != final_hashes[path]:
                overwritten += 1

    run = _platform_run(output)
    usage = run.get("usage", {})
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    result = {
        "schema_version": 1,
        "platform": run.get("platform", config.get("platform")),
        "task_id": config.get("task_id"),
        "checkpoint_count": len(checkpoints),
        "mutation_rounds": len(mutation_rows),
        "error_sequence": errors,
        "CNV-1": {"first_final_error_checkpoint": first_final},
        "CNV-2": {"convergence_instability": round(stability, 6)},
        "CNV-3": {
            "effective_round_rate": round(decreased / len(transitions), 6)
            if transitions
            else 0.0,
            "decreased": decreased,
            "increased": increased,
            "unchanged": unchanged,
        },
        "CNV-4": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cache_read_input_tokens": usage.get(
                "cache_read_input_tokens", usage.get("cached_input_tokens")
            ),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        },
        "EXP-1": {
            "scope_drift_rate": round(len(drift) / len(touched), 6) if touched else 0.0,
            "drift_files": drift,
            "allowed_patterns": allowed_patterns,
        },
        "EXP-2": {
            "overwritten_edit_rate": round(overwritten / total_revisions, 6)
            if total_revisions
            else 0.0
        },
        "EXP-3": {
            "revisited_file_rate": round(
                sum(count >= 2 for count in revision_counts.values()) / len(touched), 6
            )
            if touched
            else 0.0,
            "revision_counts": revision_counts,
        },
        "OSC-1": {"oscillated": bool(oscillating), "locations": sorted(oscillating)},
        "OSC-2": {
            "severity": round(
                sum(revision_counts[path] for path in oscillating) / len(oscillating), 6
            )
            if oscillating
            else 0.0
        },
        "DEC-2": {
            "validation_steps": sum(
                len(row.get("validations", [])) for row in checkpoints
            )
        },
        "terminal": {
            "initial_error": errors[0],
            "final_error": final_error,
            "success": final_error == 0,
            "initial_validations": checkpoints[0].get("validations", []),
            "final_validations": checkpoints[-1].get("validations", []),
        },
        "run": run,
    }
    (output / "metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
