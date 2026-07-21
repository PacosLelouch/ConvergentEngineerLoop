"""数学工具 —— T15 涉及（震荡易发）。"""


def calculate_statistics(values: list[float | None]) -> dict:
    """计算均值和中位数。

    T15 缺陷：None 处理不一致 + 多分支相互影响。
    """
    if not values:
        return {"mean": 0.0, "median": 0.0, "count": 0}

    if values[0] is None:
        raise ValueError("首个值不能为 None")

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
