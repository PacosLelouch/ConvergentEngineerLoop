"""CLI 模块 —— T09 涉及。"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="cel-eval CLI")
    parser.add_argument("command", choices=["list", "export", "stats"],
                        help="要执行的命令")
    parser.add_argument("--out", default="output.json",
                        help="输出文件路径")
    parser.add_argument("--format", choices=["json", "csv"], default="json",
                        help="输出格式")

    args = parser.parse_args()

    if args.command == "list":
        result = {"items": [1, 2, 3], "count": 3}
    elif args.command == "export":
        result = {"exported": True, "file": args.out}
    elif args.command == "stats":
        result = {"mean": 2.0, "median": 2.0}

    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"结果已写入 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
