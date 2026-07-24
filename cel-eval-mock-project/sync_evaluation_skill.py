#!/usr/bin/env python3
"""把评测专用 skill 同步到当前评测仓库的 Agent 发现目录。

该脚本只服务于本仓库的 A/B 评测编排，不参与 CEL 产品打包或常规安装。
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


EVAL_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = EVAL_ROOT.parent
SKILL_SOURCE = EVAL_ROOT / "skills" / "cel-ab-evaluation"
RELATIVE_TARGETS = (
    Path(".agents/skills/cel-ab-evaluation"),
    Path(".codebuddy/skills/cel-ab-evaluation"),
)


def directory_digest(path: Path) -> str:
    """计算目录内容与相对路径的稳定摘要。"""
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_repository_root(repository_root: Path) -> Path:
    """限制同步目标为包含本评测项目的仓库根目录。"""
    resolved = repository_root.resolve()
    if not (resolved / "cel-eval-mock-project" / "task_suite.json").is_file():
        raise ValueError(f"不是 CEL 评测仓库根目录：{resolved}")
    return resolved


def target_paths(repository_root: Path = REPOSITORY_ROOT) -> tuple[Path, ...]:
    """返回当前评测仓库的两个平台发现目录。"""
    root = validate_repository_root(repository_root)
    return tuple(root / relative for relative in RELATIVE_TARGETS)


def verify_synced(repository_root: Path = REPOSITORY_ROOT) -> tuple[Path, ...]:
    """验证两个发现副本都存在且与评测真源完全一致。"""
    if not SKILL_SOURCE.is_dir():
        raise FileNotFoundError(f"评测 skill 真源不存在：{SKILL_SOURCE}")

    source_digest = directory_digest(SKILL_SOURCE)
    targets = target_paths(repository_root)
    for target in targets:
        if not target.is_dir():
            raise FileNotFoundError(f"评测 skill 副本不存在：{target}")
        if directory_digest(target) != source_digest:
            raise RuntimeError(f"评测 skill 副本与真源不一致：{target}")
    return targets


def sync(repository_root: Path = REPOSITORY_ROOT) -> tuple[Path, ...]:
    """覆盖同步当前评测仓库的 Codex 与 CodeBuddy 发现副本。"""
    if not SKILL_SOURCE.is_dir():
        raise FileNotFoundError(f"评测 skill 真源不存在：{SKILL_SOURCE}")

    targets = target_paths(repository_root)
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_SOURCE, target)
    return verify_synced(repository_root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="同步或校验当前仓库的 CEL A/B 评测专用 skill"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只校验真源与平台发现副本，不修改文件",
    )
    args = parser.parse_args()

    targets = verify_synced() if args.check else sync()
    action = "校验通过" if args.check else "同步完成"
    print(f"CEL A/B 评测 skill {action}：")
    for target in targets:
        print(f"  {target}")
    print("该 skill 不进入 CEL 产品文件夹包、插件包或常规项目安装。")


if __name__ == "__main__":
    main()
