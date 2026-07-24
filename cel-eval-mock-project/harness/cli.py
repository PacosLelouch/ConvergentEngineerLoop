"""Command-line entry points shared by platform adapters and hooks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .isolation import verify_config_isolation
from .metrics import reduce_metrics
from .snapshot import capture_checkpoint, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--config", type=Path, required=True)
    capture_parser.add_argument("--cause", required=True)
    reduce_parser = subparsers.add_parser("reduce")
    reduce_parser.add_argument("--config", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    if args.command == "capture":
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else None
        checkpoint = capture_checkpoint(config, args.cause, event)
        print(json.dumps({"captured": checkpoint is not None}))
        return 0
    if args.command == "reduce":
        metrics = reduce_metrics(config)
        print(json.dumps(metrics, ensure_ascii=False))
        return 0
    result = verify_config_isolation(config)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
