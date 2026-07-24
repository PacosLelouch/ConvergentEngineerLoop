"""CEL A/B 对比报告生成器。

从各任务的实际数据文件中提取指标，程序化生成 comparison.yaml。
替代 orchestrator Agent 手工生成，消除模板化 delta=0 问题。

用法：
  python generate_comparison.py <output_dir>
  例如：
  python generate_comparison.py ../test-runs/codex_gpt-5.6-luna-medium_20260722T024936Z
"""

import json
import re
import sys
from pathlib import Path


def parse_pytest_summary(txt: str) -> dict:
    """从 pytest 输出中提取通过的测试数。

    处理多行输出中最后一行汇总（如 "108 passed in 3.08s"）。
    """
    passed = 0
    failed = 0
    errors = 0
    for line in txt.split("\n"):
        m = re.search(r"(\d+)\s+passed", line)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+)\s+failed", line)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+)\s+error", line)
        if m:
            errors = int(m.group(1))
    return {"pass": passed, "fail": failed, "error": errors}


def parse_diff_file(txt: str) -> dict:
    """从 diff.txt 中提取：修改文件数、新增行数、删除行数。"""
    files_changed = 0
    lines_added = 0
    lines_removed = 0

    in_changed = False
    for line in txt.split("\n"):
        # 统计 Changed files 段落的文件数
        if "--- Changed files" in line:
            in_changed = True
            continue
        if in_changed:
            if line.startswith("  ~ "):
                files_changed += 1
            elif line.startswith("---") or not line.strip():
                in_changed = False

        # 统计新增/删除文件
        if "--- Added files" in line:
            continue

    # 通过 git diff 行级统计（如果 diff 含 patch 内容）
    for line in txt.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            lines_added += 1
        if line.startswith("-") and not line.startswith("---"):
            lines_removed += 1

    # 去除二进制 diff 的干扰
    lines_added = lines_added if lines_added < 10000 else 0
    lines_removed = lines_removed if lines_removed < 10000 else 0

    return {
        "files_changed": files_changed,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
    }


def parse_agent_log(txt: str) -> dict:
    """从 agent_log.txt 中提取过程指标。

    新格式：worker 自写的 key=value 格式（以 '---' 分隔头部和对话体）。
    """
    if not txt.strip():
        return {
            "group": "unknown",
            "rounds": 0,
            "edits": 0,
            "reverts": 0,
            "test_runs": 0,
            "error_measures": 0,
            "protocol_refs": 0,
            "has_cel_language": False,
            "parse_error": "empty file",
        }

    header_lines = []
    separator_found = False
    for line in txt.split("\n"):
        line_s = line.strip()
        if line_s == "---":
            separator_found = True
            break
        header_lines.append(line_s)

    if not separator_found:
        # 旧格式：没有 --- 分隔符，使用全文启发式解析（向后兼容）
        return _parse_agent_log_legacy(txt)

    # 解析 key=value 头部
    def get_value(key: str, default=0) -> int:
        for h in header_lines:
            if h.startswith(f"{key}="):
                try:
                    return int(h.split("=", 1)[1].strip())
                except ValueError:
                    return default
        return default

    group = ""
    for h in header_lines:
        if h.startswith("group="):
            group = h.split("=", 1)[1].strip()
            break

    rounds = get_value("rounds")
    edits = get_value("edits")
    test_runs = get_value("test_runs")
    reverts = get_value("reverts")
    error_measures = get_value("error_measures")
    protocol_refs = get_value("protocol_refs")

    # 交叉污染检测：只在 Control 组的 "---" 之后体部分检测 CEL 语言
    has_cel_language = False
    if group == "control":
        cel_keywords = [
            "收敛",
            "误差度量",
            "误差下降",
            "误差上升",
            "accept",
            "rollback",
            "最小更新",
            "CEL protocol",
            "convergent",
            "cel-planner",
            "cel-test-analyst",
            "cel-debug-analyst",
            "cel-reviewer",
        ]
        body = txt.split("---", 1)[1] if "---" in txt else ""
        body_lower = body.lower()
        has_cel_language = any(kw.lower() in body_lower for kw in cel_keywords)

    result = {
        "group": group,
        "rounds": rounds,
        "edits": edits,
        "reverts": reverts,
        "test_runs": test_runs,
        "error_measures": error_measures,
        "protocol_refs": protocol_refs,
        "has_cel_language": has_cel_language,
    }

    # 检测错误标记
    if "ERROR:" in header_lines[0] if header_lines else "":
        result["parse_error"] = "worker did not write agent_log"

    return result


def _parse_agent_log_legacy(txt: str) -> dict:
    """向后兼容：解析旧格式的 agent_log（orchestrator 生成的摘要）。"""
    lines = txt.strip().split("\n")
    rounds = 0
    edits = 0
    reverts = 0
    test_runs = 0
    has_cel_language = False

    cel_keywords = [
        "收敛",
        "误差度量",
        "误差下降",
        "误差上升",
        "accept",
        "rollback",
        "最小更新",
        "CEL protocol",
        "convergent",
        "cel-planner",
        "cel-test-analyst",
        "cel-debug-analyst",
        "cel-reviewer",
    ]

    for line in lines:
        line_lower = line.lower()
        if any(kw.lower() in line_lower for kw in cel_keywords):
            has_cel_language = True
        if "round" in line_lower and ":" in line:
            rounds += 1

    # 粗略估计
    edit_keywords = ["修改", "编辑", "edit", "replace", "write", "更新"]
    for line in lines:
        if any(kw in line.lower() for kw in edit_keywords):
            edits += 1
    for line in lines:
        if "pytest" in line.lower() or "测试" in line or "test run" in line.lower():
            test_runs += 1
    for line in lines:
        if "回滚" in line or "rollback" in line.lower() or "撤回" in line:
            reverts += 1

    return {
        "group": "unknown",
        "rounds": rounds,
        "edits": edits,
        "reverts": reverts,
        "test_runs": test_runs,
        "error_measures": 0,
        "protocol_refs": 0,
        "has_cel_language": has_cel_language,
        "parse_error": "legacy format (no --- separator)",
    }


def read_file_safe(path: Path) -> str:
    """安全读取文件，不存在返回空字符串。"""
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def read_json_safe(path: Path) -> dict:
    """读取客观采集器输出；不存在或损坏时返回空字典。"""
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _validation(metrics: dict, phase: str, name: str) -> dict:
    for item in metrics.get("terminal", {}).get(f"{phase}_validations", []):
        if item.get("name") == name:
            return item
    return {}


def generate_objective_comparison(task_id: str, control: dict, cel: dict) -> dict:
    """优先使用平台事件和 checkpoint 归约结果，不读取 agent 自报。"""

    def pair(cel_value, control_value):
        return {
            "cel": cel_value,
            "control": control_value,
            "delta": cel_value - control_value,
        }

    ctrl_pytest = _validation(control, "final", "pytest")
    cel_pytest = _validation(cel, "final", "pytest")
    ctrl_initial = _validation(control, "initial", "pytest")
    cel_initial = _validation(cel, "initial", "pytest")
    result = {
        "task": task_id,
        "_data_sources": "harness metrics.json (platform events + mutation checkpoints)",
        "terminal_metrics": {
            "success": pair(
                int(cel["terminal"]["success"]), int(control["terminal"]["success"])
            ),
            "error_score": pair(
                cel["terminal"]["final_error"], control["terminal"]["final_error"]
            ),
            "test_pass": {
                **pair(cel_pytest.get("passed", 0), ctrl_pytest.get("passed", 0)),
                "init_cel": cel_initial.get("passed", 0),
                "init_control": ctrl_initial.get("passed", 0),
            },
            "test_fail": pair(
                cel_pytest.get("failed", 0) + cel_pytest.get("errors", 0),
                ctrl_pytest.get("failed", 0) + ctrl_pytest.get("errors", 0),
            ),
        },
        "process_metrics": {
            "mutation_rounds": pair(cel["mutation_rounds"], control["mutation_rounds"]),
            "CNV-2_convergence_instability": pair(
                cel["CNV-2"]["convergence_instability"],
                control["CNV-2"]["convergence_instability"],
            ),
            "CNV-3_effective_round_rate": pair(
                cel["CNV-3"]["effective_round_rate"],
                control["CNV-3"]["effective_round_rate"],
            ),
            "CNV-4_total_tokens": pair(
                cel["CNV-4"]["total_tokens"], control["CNV-4"]["total_tokens"]
            ),
            "EXP-1_scope_drift_rate": pair(
                cel["EXP-1"]["scope_drift_rate"], control["EXP-1"]["scope_drift_rate"]
            ),
            "OSC-2_severity": pair(
                cel["OSC-2"]["severity"], control["OSC-2"]["severity"]
            ),
            "DEC-2_validation_steps": pair(
                cel["DEC-2"]["validation_steps"], control["DEC-2"]["validation_steps"]
            ),
        },
        "oscillation": {
            "cel": cel["OSC-1"],
            "control": control["OSC-1"],
        },
        "scope_drift_files": {
            "cel": cel["EXP-1"]["drift_files"],
            "control": control["EXP-1"]["drift_files"],
        },
        "cross_contamination_check": {
            "cel_has_cel_language": None,
            "control_has_cel_language": None,
            "warning": None,
            "note": "数值采集不再依赖 agent_log；语言污染需从平台 transcript 单独盲检",
        },
        "consistency_check": {
            "cel_init_vs_final": "OK"
            if cel["terminal"]["initial_error"] != cel["terminal"]["final_error"]
            else "NO_CHANGE",
            "ctrl_init_vs_final": "OK"
            if control["terminal"]["initial_error"]
            != control["terminal"]["final_error"]
            else "NO_CHANGE",
        },
    }
    return result


def generate_comparison(task_dir: Path) -> dict:
    """为单个任务生成 comparison.yaml 内容。"""
    task_id = task_dir.name

    ctrl_metrics = read_json_safe(task_dir / "control" / "metrics.json")
    cel_metrics = read_json_safe(task_dir / "cel" / "metrics.json")
    if ctrl_metrics and cel_metrics:
        return generate_objective_comparison(task_id, ctrl_metrics, cel_metrics)

    # ── 读取 Control 组数据 ──
    ctrl_init_txt = read_file_safe(task_dir / "control" / "init_tests.txt")
    ctrl_tests_txt = read_file_safe(task_dir / "control" / "tests.txt")
    ctrl_diff_txt = read_file_safe(task_dir / "control" / "diff.txt")
    ctrl_log_txt = read_file_safe(task_dir / "control" / "agent_log.txt")

    # ── 读取 CEL 组数据 ──
    cel_init_txt = read_file_safe(task_dir / "cel" / "init_tests.txt")
    cel_tests_txt = read_file_safe(task_dir / "cel" / "tests.txt")
    cel_diff_txt = read_file_safe(task_dir / "cel" / "diff.txt")
    cel_log_txt = read_file_safe(task_dir / "cel" / "agent_log.txt")

    # ── 解析各数据源 ──
    ctrl_init = parse_pytest_summary(ctrl_init_txt)
    ctrl_final = parse_pytest_summary(ctrl_tests_txt)
    ctrl_diff = parse_diff_file(ctrl_diff_txt)
    ctrl_log = parse_agent_log(ctrl_log_txt)

    cel_init = parse_pytest_summary(cel_init_txt)
    cel_final = parse_pytest_summary(cel_tests_txt)
    cel_diff = parse_diff_file(cel_diff_txt)
    cel_log = parse_agent_log(cel_log_txt)

    # ── 计算 delta ──
    def delta(a, b):
        return a - b

    result = {
        "task": task_id,
        "_data_sources": "generated by generate_comparison.py (programmatic)",
        "terminal_metrics": {
            "test_pass": {
                "cel": cel_final["pass"],
                "control": ctrl_final["pass"],
                "delta": delta(cel_final["pass"], ctrl_final["pass"]),
                "init_cel": cel_init["pass"],
                "init_control": ctrl_init["pass"],
            },
            "test_fail": {
                "cel": cel_final["fail"],
                "control": ctrl_final["fail"],
                "delta": delta(cel_final["fail"], ctrl_final["fail"]),
            },
            "files_changed": {
                "cel": cel_diff["files_changed"],
                "control": ctrl_diff["files_changed"],
                "delta": delta(cel_diff["files_changed"], ctrl_diff["files_changed"]),
            },
            "lines_added": {
                "cel": cel_diff["lines_added"],
                "control": ctrl_diff["lines_added"],
                "delta": delta(cel_diff["lines_added"], ctrl_diff["lines_added"]),
            },
            "lines_removed": {
                "cel": cel_diff["lines_removed"],
                "control": ctrl_diff["lines_removed"],
                "delta": delta(cel_diff["lines_removed"], ctrl_diff["lines_removed"]),
            },
        },
        "process_metrics": {
            "worker_rounds": {
                "cel": cel_log["rounds"],
                "control": ctrl_log["rounds"],
                "delta": delta(cel_log["rounds"], ctrl_log["rounds"]),
            },
            "edit_operations": {
                "cel": cel_log["edits"],
                "control": ctrl_log["edits"],
                "delta": delta(cel_log["edits"], ctrl_log["edits"]),
            },
            "revert_count": {
                "cel": cel_log["reverts"],
                "control": ctrl_log["reverts"],
                "delta": delta(cel_log["reverts"], ctrl_log["reverts"]),
            },
            "test_runs": {
                "cel": cel_log["test_runs"],
                "control": ctrl_log["test_runs"],
                "delta": delta(cel_log["test_runs"], ctrl_log["test_runs"]),
            },
        },
        "cel_specific": {
            "error_measures": cel_log["error_measures"],
            "protocol_refs": cel_log["protocol_refs"],
        },
        "agent_log_parse_errors": {
            "cel": cel_log.get("parse_error"),
            "control": ctrl_log.get("parse_error"),
        },
        "cross_contamination_check": {
            "cel_has_cel_language": cel_log["has_cel_language"],
            "control_has_cel_language": ctrl_log["has_cel_language"],
            "warning": (
                "⚠️ CONTROL 组检出 CEL 协议语言，存在交叉污染！"
                if ctrl_log["has_cel_language"]
                else None
            ),
        },
        "consistency_check": {
            "cel_init_vs_final": "OK"
            if cel_final["pass"] != cel_init["pass"]
            else "NO_CHANGE (可能未修复或数据采集错误)",
            "ctrl_init_vs_final": "OK"
            if ctrl_final["pass"] != ctrl_init["pass"]
            else "NO_CHANGE (可能未修复或数据采集错误)",
        },
    }

    return result


def main():
    # 修复 Windows 控制台 GBK 编码问题
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    if not output_dir.exists():
        print(f"ERROR: {output_dir} 不存在")
        sys.exit(1)

    task_dirs = sorted(
        [
            d
            for d in output_dir.iterdir()
            if d.is_dir() and d.name.startswith("T") and d.name[1:].isdigit()
        ],
        key=lambda d: int(d.name[1:]),
    )

    if not task_dirs:
        print(f"ERROR: {output_dir} 中没有找到任务目录 (Txx)")
        sys.exit(1)

    print(f"处理 {len(task_dirs)} 个任务目录...")

    for task_dir in task_dirs:
        comp = generate_comparison(task_dir)
        comp_path = task_dir / "comparison.yaml"
        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump(comp, f, indent=2, ensure_ascii=False)
        print(f"  {task_dir.name}: {comp_path}")

        # 交叉污染警告
        cc = comp["cross_contamination_check"]
        if cc["warning"]:
            print(f"    ⚠️  {cc['warning']}")

        # 一致性警告
        for k, v in comp["consistency_check"].items():
            if "NO_CHANGE" in v:
                print(f"    ⚠️  {k}: {v}")

    print(f"\n完成。共处理 {len(task_dirs)} 个任务。")


if __name__ == "__main__":
    main()
