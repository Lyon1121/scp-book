"""
库存计划模块

输入: 需求预测结果 (月度)
输出: 每个SKU的安全库存、周转库存、目标库存、ABC-XYZ分类
"""
import pandas as pd
import numpy as np
from data.schemas import InventoryPlanResult
import config


def calculate_safety_stock(
    df_monthly: pd.DataFrame,
    z_factor: float = None,
) -> pd.DataFrame:
    """
    计算安全库存

    安全库存 = MAD × Z因子
    MAD = 月度实际销量与均值的平均绝对偏差

    Args:
        df_monthly: 月度销量 (列: SKU, 月份, 实际销量)
        z_factor: 安全因子 (默认取 config.Z_FACTOR)

    Returns:
        DataFrame with columns: SKU, 安全库存, MAD
    """
    if z_factor is None:
        z_factor = config.Z_FACTOR

    result = df_monthly.groupby("SKU").agg(
        月均销量=("实际销量", "mean"),
        月销量标准差=("实际销量", "std"),
    ).reset_index()

    # 近似每日MAD = 月度标准差 / sqrt(30)
    result["日均MAD"] = result["月销量标准差"] / np.sqrt(30)
    # 安全库存覆盖补货周期内的不确定性
    result["安全库存"] = (result["日均MAD"] * np.sqrt(config.REPLENISHMENT_CYCLE) * z_factor).round(0).astype(int)

    return result[["SKU", "月均销量", "月销量标准差", "安全库存"]]


def calculate_cycle_stock(
    df_monthly: pd.DataFrame,
    replenishment_cycle: int = None,
) -> pd.DataFrame:
    """
    计算周转库存

    周转库存 = 日均需求 × 补货周期 / 2

    Args:
        df_monthly: 月度销量
        replenishment_cycle: 补货周期（天）

    Returns:
        DataFrame with columns: SKU, 日均需求, 周转库存
    """
    if replenishment_cycle is None:
        replenishment_cycle = config.REPLENISHMENT_CYCLE

    result = df_monthly.groupby("SKU")["实际销量"].mean().reset_index()
    result.columns = ["SKU", "月均销量"]
    result["日均需求"] = (result["月均销量"] / 30).round(1)
    result["周转库存"] = (result["日均需求"] * replenishment_cycle / 2).round(0).astype(int)

    return result[["SKU", "日均需求", "周转库存"]]


def classify_abc(
    df_monthly: pd.DataFrame,
) -> pd.DataFrame:
    """
    ABC 分类 (按销售额累计占比)

    A类: 累计占比 0~70%
    B类: 累计占比 70~90%
    C类: 累计占比 90~100%
    """
    total_sales = df_monthly.groupby("SKU")["实际销量"].sum().reset_index()
    total_sales = total_sales.sort_values("实际销量", ascending=False)
    total_sales["累计占比"] = total_sales["实际销量"].cumsum() / total_sales["实际销量"].sum()

    total_sales["ABC分类"] = total_sales["累计占比"].apply(
        lambda x: "A" if x <= 0.70 else ("B" if x <= 0.90 else "C")
    )
    return total_sales[["SKU", "ABC分类"]]


def classify_xyz(
    df_monthly: pd.DataFrame,
) -> pd.DataFrame:
    """
    XYZ 分类 (按需求波动系数 CV)

    X类: CV ≤ 0.2 (稳定)
    Y类: CV 0.2~0.5 (中等波动)
    Z类: CV > 0.5 (高度波动)
    """
    stats = df_monthly.groupby("SKU")["实际销量"].agg(["mean", "std"]).reset_index()
    stats["CV"] = stats["std"] / stats["mean"]
    stats["CV"] = stats["CV"].fillna(0)

    stats["XYZ分类"] = stats["CV"].apply(
        lambda x: "X" if x <= 0.2 else ("Y" if x <= 0.5 else "Z")
    )
    return stats[["SKU", "XYZ分类"]]


def run_inventory_plan(
    df_monthly: pd.DataFrame,
    z_factor: float = None,
) -> pd.DataFrame:
    """
    库存计划主函数

    Args:
        df_monthly: 月度销量 DataFrame (列: SKU, 月份, 实际销量)
        z_factor: 安全因子

    Returns:
        InventoryPlanResult DataFrame
    """
    ip = InventoryPlanResult()

    # 1. 安全库存
    safety = calculate_safety_stock(df_monthly, z_factor)

    # 2. 周转库存
    cycle = calculate_cycle_stock(df_monthly)

    # 3. ABC 分类
    abc = classify_abc(df_monthly)

    # 4. XYZ 分类
    xyz = classify_xyz(df_monthly)

    # 5. 合并
    result = safety.merge(cycle, on="SKU").merge(abc, on="SKU").merge(xyz, on="SKU")

    # 6. 目标库存
    result[ip.TARGET_INVENTORY] = result["安全库存"] + result["周转库存"]

    # 7. 重命名列
    result = result.rename(columns={
        "月均销量": "月均销量",
        "日均需求": ip.AVG_DAILY_DEMAND,
        "安全库存": ip.SAFETY_STOCK,
        "周转库存": ip.CYCLE_STOCK,
        "目标库存": ip.TARGET_INVENTORY,
        "ABC分类": ip.ABC_CLASS,
        "XYZ分类": ip.XYZ_CLASS,
    })

    return result[[ip.SKU, ip.AVG_DAILY_DEMAND, ip.SAFETY_STOCK,
                    ip.CYCLE_STOCK, ip.TARGET_INVENTORY,
                    ip.ABC_CLASS, ip.XYZ_CLASS]]
