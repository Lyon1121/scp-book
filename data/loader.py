"""
CSV 数据加载 & 校验 —— 项目的"数据入口层"

所有 CSV 文件都通过这里的函数加载，统一做两件事：
  1. 读文件（处理路径、编码问题）
  2. 校验列名（确保 CSV 结构符合预期，防止上游模块拿到残废数据）

为什么要统一？
  - 上游模块不需要关心 CSV 在哪、什么编码、列名对不对
  - 加载失败立刻报错，不在下游模块里"莫名其妙地崩"
"""
import pandas as pd                             # pandas 是 Python 数据分析的核心库
from pathlib import Path                         # pathlib 处理文件路径，比字符串拼接更安全
from typing import Optional                      # Optional 表示参数"可以是 None"


def load_csv(file_path: str) -> pd.DataFrame:
    """
    加载一个 CSV 文件并返回 pandas DataFrame

    步骤：
      1. 检查文件是否存在（不存在直接报错，不返回 None 让下游蒙在鼓里）
      2. 用 utf-8-sig 编码读取（处理 Windows 下 Excel 导出的 BOM 头）
      3. 打印加载日志（行数+列数，方便排查数据量对不对）

    Args:
        file_path: CSV 文件的绝对路径或相对路径，如 "C:/data/sales.csv"

    Returns:
        加载完成的 pd.DataFrame，列名即为 CSV 第一行

    Raises:
        FileNotFoundError: 文件路径不存在时抛出
    """
    path = Path(file_path)                       # 将字符串路径转为 Path 对象，方便跨平台操作
    if not path.exists():                        # 检查文件是否真的存在
        raise FileNotFoundError(f"文件不存在: {file_path}")  # 不存在就立即报错，不让下游拿到空数据

    # 2. 尝试多种编码读取（用户 CSV 可能来自 Excel GBK 导出）
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")  # 先试 utf-8-sig
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="gbk")         # 失败则用 gbk（中文 Windows 常见编码）
    print(f"  [加载] {path.name}: {len(df)} 行, {len(df.columns)} 列")  # 日志：告诉用户读到了多少数据
    return df                                    # 返回 DataFrame 给调用方


def validate_columns(df: pd.DataFrame, required_cols: list, label: str = "数据") -> pd.DataFrame:
    """
    校验 DataFrame 的列名是否完整

    为什么需要这个？
      CSV 可能被手动编辑过、列名写错了、或者少了一列。
      如果不在入口处校验，下游模块用 df["某个不存在的列"] 会直接 KeyError，
      调用方根本不知道是数据问题还是代码问题。

    校验逻辑：
      遍历 required_cols，检查每一列是否存在于 df.columns 中。
      缺失的列会被收集起来，最后一次性报错（而不是报一个修一个）。

    Args:
        df: 待校验的 DataFrame（通常是 load_csv 的结果）
        required_cols: 必需列名的列表，如 ["SKU", "日期", "销量"]
        label: 数据标签，出现在报错信息中帮助定位是哪个文件出了问题

    Returns:
        校验通过的同一个 DataFrame（原样返回，方便链式调用）

    Raises:
        ValueError: 当缺少必需列时，显示缺失列、当前列、需要列
    """
    # 列表推导式：找出 required_cols 中哪些列不在 df.columns 里
    missing = [c for c in required_cols if c not in df.columns]
    if missing:                                  # 如果有缺失列
        raise ValueError(                        # 抛出详细错误，包含三行信息：
            f"[{label}] 缺少必需列: {missing}\n"  #   1. 哪个文件 + 缺了哪些列
            f"  当前列: {list(df.columns)}\n"     #   2. 当前实际的列名
            f"  需要列: {required_cols}"          #   3. 应该有什么列
        )
    return df                                    # 校验通过，返回原 DataFrame


def load_and_validate(file_path: str, required_cols: list, label: Optional[str] = None) -> pd.DataFrame:
    """
    加载 + 校验一步到位（最常用的快捷函数）

    相当于 load_csv() + validate_columns() 的封装。
    大多数情况下只需要调这一个函数就够了。

    Args:
        file_path: CSV 文件路径
        required_cols: 必需列名列表
        label: 数据标签（可选），不传则用文件名 stem 部分作为标签

    Returns:
        校验通过的 DataFrame

    Example:
        df = load_and_validate("sales.csv", ["SKU", "日期", "销量"], label="销售数据")
    """
    if label is None:                            # 如果调用方没传 label
        label = Path(file_path).stem             #   自动用文件名（不含扩展名）作为标签
    df = load_csv(file_path)                     # 第1步：加载 CSV
    return validate_columns(df, required_cols, label)  # 第2步：校验列名，返回结果
