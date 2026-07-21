"""数学工具模块 —— T15 涉及（震荡易发）。

main 分支：所有分支对 None 的返回值不一致（刻意如此，为 T15 准备）。
T15 任务：统一 None 处理（跳过 None，返回剩余数据统计）。
"""

import math


def calculate_statistics(values: list[float | None]) -> dict:
    """计算均值和中位数。

    ⚠️ main 分支刻意保留不一致的 None 处理，作为 T15 的初始态。
    实际正确实现应跳过 None 值。
    """
    if not values:
        return {"mean": 0.0, "median": 0.0, "count": 0}

    # 分支 1：全部 None → 抛异常
    if all(v is None for v in values):
        raise ValueError("所有值均为 None")

    # 分支 2：有 None 混入 → 部分结果
    # 不一致：这里 None 参与排序会报错
    clean = [v for v in values if v is not None]

    if not clean:
        return {"mean": 0.0, "median": 0.0, "count": 0}

    n = len(clean)
    mean = sum(clean) / n

    sorted_vals = sorted(clean)
    if n % 2 == 1:
        median = sorted_vals[n // 2]
    else:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    return {"mean": round(mean, 4), "median": round(median, 4), "count": n}
