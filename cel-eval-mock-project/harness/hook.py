"""Synchronous Codex PostToolUse hook entry point."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .snapshot import capture_checkpoint, load_config


def main() -> int:
    config_path = os.environ.get("CEL_METRICS_CONFIG")
    if not config_path:
        print("CEL_METRICS_CONFIG is not set", file=sys.stderr)
        return 0
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        capture_checkpoint(load_config(Path(config_path)), "post_tool_use", event)
    except Exception as exc:  # observation must never block the agent's tool call
        print(f"CEL metrics hook failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
