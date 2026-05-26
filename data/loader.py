"""
CSV 数据加载 & 校验
"""
import pandas as pd
from pathlib import Path
from typing import Optional


def load_csv(file_path: str) -> pd.DataFrame:
    """
    加载 CSV 文件为 DataFrame

    Args:
        file_path: CSV 文件路径

    Returns:
        pd.DataFrame

    Raises:
        FileNotFoundError: 文件不存在
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    df = pd.read_csv(path, encoding="utf-8-sig")
    print(f"  [加载] {path.name}: {len(df)} 行, {len(df.columns)} 列")
    return df


def validate_columns(df: pd.DataFrame, required_cols: list, label: str = "数据") -> pd.DataFrame:
    """
    校验 DataFrame 是否包含必需列

    Args:
        df: 待校验 DataFrame
        required_cols: 必需列名列表
        label: 数据标签（用于报错提示）

    Returns:
        原 DataFrame（通过校验）

    Raises:
        ValueError: 缺少必需列时的详细报错
    """
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"[{label}] 缺少必需列: {missing}\n"
            f"  当前列: {list(df.columns)}\n"
            f"  需要列: {required_cols}"
        )
    return df


def load_and_validate(file_path: str, required_cols: list, label: Optional[str] = None) -> pd.DataFrame:
    """
    加载 CSV 并校验列名（一步到位）

    Args:
        file_path: CSV 路径
        required_cols: 必需列名
        label: 数据标签

    Returns:
        校验通过的 DataFrame
    """
    if label is None:
        label = Path(file_path).stem
    df = load_csv(file_path)
    return validate_columns(df, required_cols, label)
