"""Task-specific acceptance checks kept outside the agent workspace."""

from __future__ import annotations

import ast
import csv
import importlib
import io
import re
import sys
from pathlib import Path
from typing import Callable


Check = tuple[str, Callable[[], None]]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _text(workspace: Path, relative: str) -> str:
    path = workspace / relative
    _require(path.exists(), f"missing {relative}")
    return path.read_text(encoding="utf-8", errors="replace")


def _t05(workspace: Path) -> list[Check]:
    def role_contract() -> None:
        text = _text(workspace, "tests/test_auth.py")
        _require(
            'payload["role"] == "Admin"' not in text,
            "test still contradicts the lowercase admin contract",
        )

    def deterministic_session_test() -> None:
        text = _text(workspace, "tests/test_session.py")
        tree = ast.parse(text)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        _require("random" not in imports, "session test still depends on random timing")
        _require(
            "time.time" not in text, "session test still depends on wall-clock timing"
        )

    return [
        ("role contract", role_contract),
        ("deterministic session boundary", deterministic_session_test),
    ]


def _t10(workspace: Path) -> list[Check]:
    def python_is_pinned() -> None:
        workflow = _text(workspace, ".github/workflows/ci.yml")
        versions = re.findall(r"python-version\s*:\s*['\"]?([^'\"\s]+)", workflow)
        _require(bool(versions), "CI has no python-version")
        _require(
            all(value == "3.11" for value in versions),
            f"unlocked Python versions: {versions}",
        )

    def database_url_is_supplied() -> None:
        workflow = _text(workspace, ".github/workflows/ci.yml")
        effective_lines = [
            line for line in workflow.splitlines() if not line.lstrip().startswith("#")
        ]
        _require(
            "DATABASE_URL" in "\n".join(effective_lines),
            "tests job has no DATABASE_URL",
        )

    def dependencies_are_exact() -> None:
        requirements = _text(workspace, "requirements.txt")
        specs = [
            line.strip()
            for line in requirements.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        _require(bool(specs), "requirements.txt is empty")
        _require(all("==" in spec for spec in specs), f"non-exact dependency: {specs}")

    return [
        ("Python 3.11 pin", python_is_pinned),
        ("DATABASE_URL", database_url_is_supplied),
        ("exact dependency pins", dependencies_are_exact),
    ]


def _t14(workspace: Path) -> list[Check]:
    def runtime_contract() -> None:
        sys.path.insert(0, str(workspace))
        try:
            sys.modules.pop("src.export", None)
            module = importlib.import_module("src.export")
            _require(
                module.export_csv([]) == "", "empty input must return an empty string"
            )
            data = [{"name": "Doe, Jane", "note": 'said "hello"'}]
            restored = list(csv.DictReader(io.StringIO(module.export_csv(data))))
            _require(
                restored == data, "CSV quoting does not round-trip special characters"
            )
        finally:
            sys.path.pop(0)

    def explicit_utf8_file_output() -> None:
        source = _text(workspace, "src/export.py").replace(" ", "")
        _require(
            'encoding="utf-8"' in source or "encoding='utf-8'" in source,
            "file output encoding is implicit",
        )

    def readme_contract() -> None:
        readme = _text(workspace, "README.md").lower()
        _require(
            "csv" in readme and ("empty" in readme or "空数据" in readme),
            "README omits empty CSV behavior",
        )

    return [
        ("empty/special-character runtime", runtime_contract),
        ("explicit UTF-8 output", explicit_utf8_file_output),
        ("README behavior", readme_contract),
    ]


def _t17(workspace: Path) -> list[Check]:
    def no_module_global_lock() -> None:
        tree = ast.parse(_text(workspace, "src/counter.py"))
        for node in tree.body:
            value = (
                node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
            )
            if isinstance(value, ast.Call):
                name = (
                    value.func.attr
                    if isinstance(value.func, ast.Attribute)
                    else getattr(value.func, "id", "")
                )
                _require(
                    name not in {"Lock", "RLock", "Semaphore"},
                    "synchronization must be per counter instance",
                )

    return [("no module-global synchronization", no_module_global_lock)]


def _t19(workspace: Path) -> list[Check]:
    def migration_guide() -> None:
        text = _text(workspace, "docs/legacy-parser-migration.md").lower()
        _require("streaming" in text, "migration guide omits streaming mode")
        _require(
            "compat" in text or "兼容" in text, "migration guide omits compatibility"
        )

    return [("migration guide", migration_guide)]


def _t20(workspace: Path) -> list[Check]:
    def evidence_based_documentation() -> None:
        text = _text(workspace, "docs/weather-api.md").lower()
        _require(
            "main" in text and "temp" in text,
            "documentation still omits nested main.temp",
        )
        _require(
            "error" in text or "错误" in text, "documentation omits error responses"
        )

    return [("observed response contract", evidence_based_documentation)]


CHECKS = {
    "T05": _t05,
    "T10": _t10,
    "T14": _t14,
    "T17": _t17,
    "T19": _t19,
    "T20": _t20,
}


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: task_acceptance.py TASK_ID WORKSPACE", file=sys.stderr)
        return 2
    task_id = sys.argv[1]
    workspace = Path(sys.argv[2]).resolve()
    checks = CHECKS.get(task_id, lambda _: [])(workspace)
    passed = 0
    failures: list[str] = []
    for name, check in checks:
        try:
            check()
            passed += 1
        except Exception as exc:
            failures.append(f"{name}: {exc}")
    for failure in failures:
        print(f"FAILED {failure}")
    print(f"{passed} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
