"""输出写入模块 —— T18 涉及。

将验证后的数据写入文件，确保异常时清理临时文件。
"""

import os
import tempfile
from .validator import validate, ValidationError


def write_output(data: dict, filepath: str) -> str:
    """将数据写入指定文件。

    使用临时文件 + 原子重命名策略：
    1. 先写入临时文件
    2. 写入成功后重命名为目标文件
    3. 任何异常都清理临时文件

    Args:
        data: 要写入的数据字典（需先通过 validate 验证）
        filepath: 目标文件路径

    Returns:
        写入的文件路径

    Raises:
        ValidationError: 数据验证失败
        OSError: 文件写入失败
    """
    # 验证数据
    validate(data)

    tmp_path = None
    try:
        # 写入临时文件
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

        # 原子重命名
        os.replace(tmp_path, filepath)
        tmp_path = None  # 已重命名，不再需要清理

    except (ValidationError, OSError):
        # 异常时清理临时文件
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return filepath
