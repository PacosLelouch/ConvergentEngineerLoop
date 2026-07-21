#!/usr/bin/env python3
"""generate_task_branches.py —— 从 main 分支生成全部 15 个任务分支。

用法：
    python generate_task_branches.py

前置条件：
    - 当前在 cel-eval-mock-project 目录下
    - main 分支存在，所有文件正确，52 个测试全部通过
    - git 工作区干净（无未提交修改）

生成后：
    task/T01-init ... task/T15-init   （各任务初始态，含故意缺陷）
    task/T01-expected ... task/T15-expected （各任务的预期完成态）

注意：此脚本直接修改文件并提交。运行前请确认 main 分支是干净的。
"""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    print(f"  $ {cmd}")
    return subprocess.run(cmd, shell=True, cwd=ROOT, check=check, capture_output=True, text=True)


def git(cmd: str) -> None:
    run(f"git {cmd}")


def write(path: str, content: str) -> None:
    """写入文件，确保父目录存在。"""
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def apply_defects(file_mods: dict[str, str]) -> None:
    """对指定文件写入缺陷内容。key=文件路径, value=新内容。"""
    for fpath, content in file_mods.items():
        write(fpath, content)


def create_task_branch(task_id: str, defect_mods: dict[str, str],
                       expected_mods: dict[str, str] = None) -> None:
    """创建一个任务的 init 和 expected 分支。

    Args:
        task_id: 如 "T01"
        defect_mods: {文件路径: 缺陷内容} 的字典
        expected_mods: {文件路径: 修复后内容}，None 表示与 main 相同
    """
    init_branch = f"task/{task_id}-init"
    expected_branch = f"task/{task_id}-expected"

    # --- 创建 init 分支 ---
    git(f"checkout -b {init_branch} main")
    if defect_mods:
        apply_defects(defect_mods)
    git("add -A")
    git(f'commit -m "task/{task_id}: introduce defects for CEL evaluation" --allow-empty')

    # --- 创建 expected 分支 ---
    git(f"checkout -b {expected_branch} {init_branch}")
    if expected_mods:
        apply_defects(expected_mods)
    else:
        # expected 与 main 相同 — 恢复所有被修改的文件
        for fpath in defect_mods:
            git(f"checkout main -- {fpath}")
    git("add -A")
    git(f'commit -m "task/{task_id}: expected fix for CEL evaluation" --allow-empty')

    git("checkout main")
    print(f"  [OK] {task_id}: {init_branch} + {expected_branch}")


# ============================================================
# 各任务缺陷定义
# ============================================================

def create_all_branches():
    print("=" * 60)
    print("生成 CEL A/B 评测任务分支")
    print("=" * 60)

    # 确保从干净 main 开始
    git("checkout main")
    git("status --porcelain")
    result = subprocess.run("git status --porcelain", shell=True, cwd=ROOT,
                            capture_output=True, text=True)
    if result.stdout.strip():
        print("WARN: working tree is not clean, please commit or stash changes first")
        sys.exit(1)

    # -------- T01: 代码开发 · 单文件 Bug --------
    create_task_branch("T01", {
        "src/user_service.py": '''"""用户服务 —— T01 涉及。"""

from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


_USERS = {
    1: User(id=1, name="Alice"),
    2: User(id=2, name="Bob"),
}


def get_user_by_id(user_id: int) -> User | None:
    """按 ID 查询用户，不存在时返回 None。

    ⚠️ T01 缺陷：缺少 None 检查，user_id 不存在时访问 user.name 会抛 NoneTypeError。
    """
    user = _USERS.get(user_id)
    # 缺陷：缺少 if user is None: return None
    return user
''',
        "tests/test_user_service.py": '''"""T01 用户服务测试 —— init 分支 test_get_user_not_found 失败。"""

import pytest
from src.user_service import get_user_by_id, User


def test_get_existing_user():
    user = get_user_by_id(1)
    assert user is not None
    assert user.name == "Alice"


def test_get_another_user():
    user = get_user_by_id(2)
    assert user is not None
    assert user.name == "Bob"


def test_get_user_not_found():
    """不存在的用户应返回 None —— init 分支：此测试会因 NoneTypeError 而失败。"""
    user = get_user_by_id(999)
    assert user is None


def test_user_dataclass():
    u = User(id=3, name="Charlie")
    assert u.id == 3
    assert u.name == "Charlie"
''',
    })

    # -------- T02: 代码开发 · 跨文件 Bug --------
    create_task_branch("T02", {
        "src/payment.py": '''"""支付服务 —— T02 涉及。"""

import logging
from .notification import send_receipt

logger = logging.getLogger(__name__)

_USER_EMAILS = {1: "alice@test.com", 2: "bob@test.com"}


def process_payment(user_id: int, amount: float) -> dict:
    """处理支付，成功后发送收据。

    ⚠️ T02 缺陷：
    1. 调用 send_receipt 时缺少 user_email 参数。
    2. send_receipt 异常未捕获（会传播导致支付回滚假象）。
    """
    logger.info("用户 %d 支付 %.2f", user_id, amount)

    # 缺陷：缺少 user_email 参数
    send_receipt(amount)

    return {"status": "success", "user_id": user_id, "amount": amount}
''',
        "tests/test_payment.py": '''"""T02 支付测试 —— init 分支 test_payment_with_receipt 失败。"""

import pytest
from unittest.mock import patch
from src.payment import process_payment


def test_process_payment_success():
    result = process_payment(user_id=1, amount=99.99)
    assert result["status"] == "success"


def test_process_payment_different_user():
    result = process_payment(user_id=2, amount=50.0)
    assert result["status"] == "success"


def test_payment_with_receipt():
    """init 分支：此测试因调用 send_receipt 参数不足而失败。"""
    result = process_payment(user_id=1, amount=10.0)
    assert result["status"] == "success"


def test_payment_receipt_failure_does_not_rollback():
    """init 分支：send_receipt 异常会传播，此测试失败。"""
    with patch("src.payment.send_receipt", side_effect=Exception("SMTP error")):
        result = process_payment(user_id=1, amount=10.0)
        assert result["status"] == "success"


def test_payment_invalid_user_defaults_email():
    result = process_payment(user_id=999, amount=5.0)
    assert result["status"] == "success"
''',
    })

    # -------- T03: 代码开发 · 功能实现 --------
    create_task_branch("T03", {
        "src/calculator.py": '''"""计算器模块 —— T03 涉及。"""

from .errors import DivisionByZeroError


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    """除法，b=0 时抛出 DivisionByZeroError。

    ⚠️ T03 缺陷：函数体为 pass，待实现。
    """
    pass
''',
        "tests/test_calculator.py": '''"""T03 计算器测试 —— init 分支 test_divide 系列失败。"""

import pytest
from src.calculator import add, subtract, multiply, divide
from src.errors import DivisionByZeroError


def test_add():
    assert add(1, 2) == 3


def test_subtract():
    assert subtract(5, 3) == 2


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide_normal():
    """init 分支：divide 函数未实现，此测试失败。"""
    assert divide(10, 2) == 5


def test_divide_by_zero():
    """init 分支：divide 函数未实现，此测试失败。"""
    with pytest.raises(DivisionByZeroError):
        divide(10, 0)
''',
    })

    # -------- T04: 代码开发 · 只修 Bug 不重构 --------
    create_task_branch("T04", {
        "src/data_processor.py": '''"""数据处理模块 —— T04 涉及。"""


def transform_data(data: list) -> list:
    """对输入列表进行转换。

    ⚠️ T04 缺陷：空列表返回 None 而非 []。
    函数剩余部分故意包含代码风格问题（可作为范围漂移诱饵）。
    """
    if not data: return None
    result = []
    for item in data:
        if item is not None:
            result.append(item * 2)
    return result
''',
    })

    # -------- T05: 测试工程 · 失败测试修复 --------
    create_task_branch("T05", {
        "src/auth.py": '''"""鉴权模块 —— T05 涉及。"""

import time
from .errors import AuthError

_TOKENS: dict[str, dict] = {
    "valid-token": {"user": "admin", "exp": 9999999999},
    "expired-token": {"user": "admin", "exp": 0},
}


def validate_token(token: str) -> dict:
    """验证 token，返回 payload。

    ⚠️ T05 缺陷：过期 token 返回 200 语义（代码 bug），而非抛 AuthError。
    """
    payload = _TOKENS.get(token)
    if payload is None:
        raise AuthError("无效 token")
    if payload["exp"] < time.time():
        # 缺陷：应抛 AuthError，却返回了正常响应
        return {"status": "ok"}
    return {"user": payload["user"], "role": "Admin"}
''',
        "tests/test_auth.py": '''"""T05 鉴权测试 —— init 分支有 3 个失败。"""

import pytest
from src.auth import validate_token
from src.errors import AuthError


def test_validate_valid_token():
    payload = validate_token("valid-token")
    assert payload["user"] == "admin"
    assert payload["role"] == "Admin"   # main 分支返回 "Admin"，测试已适配


def test_validate_expired_token():
    """过期 token 应抛 AuthError —— init 分支：代码返回 200 而非抛异常。"""
    with pytest.raises(AuthError):
        validate_token("expired-token")


def test_validate_invalid_token():
    with pytest.raises(AuthError):
        validate_token("not-a-token")


def test_validate_token_returns_role():
    payload = validate_token("valid-token")
    assert payload["role"] == "admin"  # ⚠️ 大小写不一致：代码返回 "Admin" 但测试期望 "admin"
''',
        "tests/test_session.py": '''"""T05 会话测试 —— init 分支为 Flaky 测试。"""

import time
import random


def test_session_timeout_boundary():
    """⚠️ Flaky 测试：依赖 random，偶尔失败。"""
    start = time.time()
    # 缺陷：用 random 引入不确定性
    ttl = 300 + random.randint(-10, 10)
    expired = (time.time() - start) > ttl
    assert not expired
''',
    })

    # -------- T06: 测试工程 · 覆盖率缺口 --------
    create_task_branch("T06", {
        # T06：函数正确，只缺测试覆盖。保持 main 的 string_utils.py 不变。
        # 仅修改测试文件，保留 3 个基础测试
        "tests/test_string_utils.py": '''"""T06 字符串工具测试 —— init 分支缺 3 种边界覆盖。"""

from src.string_utils import truncate


def test_truncate_short_text():
    assert truncate("hello", 10) == "hello"


def test_truncate_long_text():
    assert truncate("hello world", 5) == "hello..."


def test_truncate_exact_length():
    assert truncate("hello", 5) == "hello"

# 缺失测试：
# - test_truncate_none_input     (text=None)
# - test_truncate_negative_max   (max_len=-1)
# - test_truncate_multibyte_chars (中文等多字节字符)
''',
    })

    # -------- T07: 日志调试 · 定位根因 --------
    create_task_branch("T07", {
        "src/db_config.py": '''"""数据库配置模块 —— T07 涉及。"""

# ⚠️ T07 缺陷：端口错误（5433 应为 5432），导致连接失败。
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "testdb",
    "user": "testuser",
    "password": "testpass",
}
''',
    })

    # -------- T08: 代码审查 · Review Comments --------
    create_task_branch("T08", {
        "src/api.py": '''"""API 模块 —— T08 涉及。"""

from dataclasses import dataclass


@dataclass
class QueryRequest:
    table: str
    filters: dict | None = None


def list_users() -> dict:
    return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "total": 2}


def get_user(user_id: int) -> dict:
    """⚠️ T08 缺陷：缺少输入校验（SQL 注入风险）。"""
    return {"id": user_id, "name": f"User{user_id}"}


def query_table(request: QueryRequest) -> dict:
    """⚠️ T08 缺陷：缺少 table 名白名单校验（SQL 注入风险）。"""
    x = 0  # ⚠️ 变量命名 x
    return {"table": request.table, "rows": x}
''',
        "src/utils.py": '''"""工具函数 —— T08 涉及。"""

import json


# ⚠️ T08 缺陷：缺少 docstring
def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)
''',
    })

    # -------- T09: 文档编写 · 文档同步 --------
    create_task_branch("T09", {
        "README.md": '''# cel-eval-mock-project

## 安装

```bash
pip install .
```

## 运行测试

```bash
pytest
```

## 使用

```bash
python -m src.cli list --output-dir result.json
python -m src.cli export --output-dir data.csv
python -m src.cli stats --output-dir stats.json
```

> ⚠️ T09 缺陷：安装命令过时（应为 pip install -e .）、CLI 参数 --output-dir 已改名 --out。
''',
    })

    # -------- T10: Harness 工程 · CI 修复 --------
    create_task_branch("T10", {
        ".github/workflows/ci.yml": '''name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"            # ⚠️ T10 缺陷：版本模糊
      - run: pip install ruff
      - run: ruff check src/
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"            # ⚠️ T10 缺陷：版本模糊
      - run: pip install -e .
      - run: pip install pytest
      - run: pytest
      # ⚠️ T10 缺陷：缺少 DATABASE_URL 环境变量
''',
        "requirements.txt": '''pytest>=7.0
# ⚠️ T10 缺陷：依赖版本未锁定
''',
    })

    # -------- T11: 架构设计 · 模块拆分 --------
    # T11 的 init 分支与 main 相同（monolith.py 已经混杂了认证/数据库/缓存）。
    # 但是 docs/architecture.md 需要缺失。
    create_task_branch("T11", {
        # T11: main 的 monolith.py 已经是混杂态，直接使用。
        # 只需确保 docs/architecture.md 不存在。
    })

    # -------- T12: 项目设计 · 需求澄清 --------
    # T12 的 init 分支与 main 相同（raw-requirements.md 已存在）。
    create_task_branch("T12", {})

    # -------- T13: 交叉验证 · 计划-代码一致性 --------
    create_task_branch("T13", {
        "docs/plan.md": '''# 项目计划（T13 交叉验证用）

> init 分支：计划标记与代码实际存在不一致。

## 模块清单

| 编号 | 模块 | 标记 | 备注 |
|------|------|:----:|------|
| P1 | user_service: 用户 CRUD | done | |
| P2 | payment: 支付处理 | done | |
| P3 | notification: 通知发送 | done | |
| P4 | calculator: 计算器 | done | |
| P5 | data_processor: 数据转换 | done | |
| P6 | report: 报告生成 | done | |
| P7 | auth: 鉴权 | done | |
| P8 | string_utils: 字符串工具 | done | |
| P9 | db_connection: 数据库连接 | done | |
| P10 | api: API 模块 | done | ⚠️ T13 缺陷: get_user 缺输入校验，标记应为 partial |
| P11 | cli: 命令行接口 | done | |
| P12 | monolith: 单体拆分 | done | ⚠️ T13 缺陷: 未拆分，标记应为 undone |
| P13 | export: CSV 导出 | done | |
| P14 | math_utils: 统计计算 | done | ⚠️ T13 缺陷: None 处理不一致，标记应为 partial |
| P15 | config: 应用配置 | done | |
''',
    })

    # -------- T14: 多域组合 · Bug + 测试 + 文档 --------
    create_task_branch("T14", {
        "src/export.py": '''"""导出模块 —— T14 涉及。"""

import csv
import io


def export_csv(data: list[dict], filepath: str | None = None) -> str:
    """将字典列表导出为 CSV 格式。

    ⚠️ T14 缺陷：空数据时崩溃（缺乏防御）。
    """
    output = io.StringIO()
    # 缺陷：data 为空时 data[0] 抛 IndexError
    fieldnames = list(data[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

    result = output.getvalue()
    output.close()

    if filepath:
        with open(filepath, "w", newline="") as f:
            f.write(result)

    return result
''',
        "tests/test_export.py": '''"""T14 导出测试 —— init 分支 test_export_csv_empty_data 失败。"""

from src.export import export_csv


def test_export_csv_basic():
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
    result = export_csv(data)
    assert "name,age" in result
    assert "Alice" in result


def test_export_csv_empty_data():
    """init 分支：空数据时 export_csv 崩溃（IndexError）。"""
    result = export_csv([])
    assert result == ""

# 缺失测试：test_export_csv_special_chars（特殊字符）
''',
    })

    # -------- T15: 震荡易发 · 修一个断一个 --------
    create_task_branch("T15", {
        "src/math_utils.py": '''"""数学工具模块 —— T15 涉及（震荡易发）。

⚠️ T15 init 分支：None 处理不一致 + 多分支相互影响。
"""


def calculate_statistics(values: list[float | None]) -> dict:
    """计算均值和中位数。"""
    if not values:
        return {"mean": 0.0, "median": 0.0, "count": 0}

    # 分支 1: 第一个元素为 None → 抛异常
    if values[0] is None:
        raise ValueError("首个值不能为 None")

    # 分支 2: 有 None 混入 → 部分结果（但不稳定）
    clean = []
    for v in values:
        if v is not None:
            clean.append(v)

    if not clean:
        return {"mean": 0.0, "median": 0.0, "count": 0}

    n = len(clean)
    mean = sum(clean) / n

    # 分支 3: 排序时未处理 None
    sorted_vals = sorted(clean)
    if n % 2 == 1:
        median = sorted_vals[n // 2]
    else:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    return {"mean": round(mean, 4), "median": round(median, 4), "count": n}
''',
        "tests/test_math_utils.py": '''"""T15 数学工具测试 —— init 分支 5 个失败。"""

import pytest
from src.math_utils import calculate_statistics


def test_normal_values():
    result = calculate_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["count"] == 5
    assert result["mean"] == 3.0


def test_even_count():
    result = calculate_statistics([1.0, 2.0, 3.0, 4.0])
    assert result["count"] == 4
    assert result["median"] == 2.5


def test_all_none_raises():
    """init 分支：全部 None 因首个为 None 而抛异常。"""
    with pytest.raises(ValueError):
        calculate_statistics([None, None, None])


def test_mixed_none():
    """init 分支：None 在第一个位置抛异常（而非跳过）。"""
    with pytest.raises(ValueError):
        calculate_statistics([None, 1.0, 3.0])


def test_mixed_none_middle():
    """init 分支：None 在中间应该跳过。"""
    result = calculate_statistics([1.0, None, 3.0])
    assert result["count"] == 2
    assert result["mean"] == 2.0


def test_empty_list():
    result = calculate_statistics([])
    assert result["count"] == 0


def test_negative_values():
    result = calculate_statistics([-5.0, 0.0, 5.0])
    assert result["mean"] == 0.0
''',
    })

    # ============================================================
    print("\n" + "=" * 60)
    print("全部 15 个任务分支生成完成！")
    print("=" * 60)
    git("checkout main")
    print("\n分支列表：")
    run("git branch")


if __name__ == "__main__":
    create_all_branches()
