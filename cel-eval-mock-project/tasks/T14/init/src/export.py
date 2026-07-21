"""导出模块 —— T14 涉及。"""

import csv
import io


def export_csv(data: list[dict], filepath: str | None = None) -> str:
    """T14 缺陷：空数据时崩溃（缺乏防御）。"""
    output = io.StringIO()
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
