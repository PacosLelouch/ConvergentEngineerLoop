"""输出写入模块 —— T18 涉及。

⚠️ 已知缺陷：验证失败时不清理临时文件，残留 .tmp 文件。
"""

import os
import tempfile
from .validator import validate, ValidationError


def write_output(data: dict, filepath: str) -> str:
    """将数据写入指定文件。

    使用临时文件 + 原子重命名。

    Args:
        data: 要写入的数据字典
        filepath: 目标文件路径

    Returns:
        写入的文件路径
    """
    # 先写入临时文件
    dir_name = os.path.dirname(filepath) or "."
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=dir_name,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tmp:
        for key, value in data.items():
            tmp.write(f"{key}: {value}\n")
        tmp_path = tmp.name

    # 验证数据（在临时文件已创建之后）  # ← 缺陷：验证失败时不清理 tmp_path
    validate(data)

    # 原子重命名
    os.replace(tmp_path, filepath)
    return filepath
