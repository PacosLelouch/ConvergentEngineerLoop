"""导出模块 —— T14 涉及。"""

import csv
import io


def export_csv(data: list[dict], filepath: str | None = None) -> str:
    """将字典列表导出为 CSV 格式。

    main 分支已正确处理空数据。
    T14 测试分支空数据时崩溃（缺乏防御）。
    """
    if not data:
        return ""

    output = io.StringIO()
    if data:
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
