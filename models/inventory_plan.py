"""
库存计划模块 —— 确定"每个 SKU 该备多少货"

输入: 需求预测结果（月度实际销量）
输出: 安全库存、周转库存、目标库存、ABC-XYZ 分类

库存 = 安全库存 + 周转库存
  安全库存: 应对"不确定性"（需求波动、供应延迟）
  周转库存: 应对"日常消耗"（补货周期内的正常销量）

ABC-XYZ 分类:
  ABC 按销售额贡献（抓重点产品）
  XYZ 按需求波动（区分稳定品和波动品）
  组合后形成 9 宫格策略矩阵，如 AX = 高价值+稳定 → 重点管理
"""
import pandas as pd                        # 数据分析
import numpy as np                         # 数值计算
from data.schemas import InventoryPlanResult  # 库存计划输出列名常量
import config                              # 全局参数（Z因子、补货周期等）


def calculate_safety_stock(
    df_monthly: pd.DataFrame,
    z_factor: float = None,                # Optional, 不传就用 config 里的默认值
) -> pd.DataFrame:
    """
    计算安全库存 —— "为了应对不确定性多备的缓冲量"

    公式推导（供应链经典公式）：
      安全库存 = Z × σ × √L

      其中:
        Z  = 安全因子（查正态分布表，95%服务水平 → Z=1.65）
        σ  = 需求的标准差（用月度销量标准差估算日标准差）
        L  = 补货提前期/周期（这里用补货周期 15 天）

    为什么是 √L？
      统计学原理：多个独立天的需求波动叠加，总方差 = 天方差 × 天数，
      总标准差 = 日标准差 × √天数。所以覆盖 L 天的不确定性需要 ×√L。

    MAD vs 标准差：
      这里用标准差近似 MAD（MAD ≈ 0.8 × 标准差），
      所以公式等价于 Z × MAD × √L / 0.8。

    Args:
        df_monthly: 月度销量 DataFrame（列: SKU, 月份, 实际销量）
        z_factor: 安全因子 Z（None 则取 config.Z_FACTOR = 1.65）

    Returns:
        DataFrame: SKU, 月均销量, 月销量标准差, 安全库存
    """
    if z_factor is None:                   # 没传 Z 因子就用全局配置
        z_factor = config.Z_FACTOR         # 默认 1.65（95% 服务水平）

    # pandas 的 groupby + agg：对每个 SKU 计算月均销量和标准差
    result = df_monthly.groupby("SKU").agg(  # agg 是一次性做多个聚合
        月均销量=("实际销量", "mean"),         #   聚合1：均值
        月销量标准差=("实际销量", "std"),       #   聚合2：标准差（波动程度）
    ).reset_index()                         # groupby 后索引变成 SKU，reset_index 恢复为普通列

    # 日标准差 ≈ 月标准差 / √30（假设每月30天，各天独立）
    result["日均MAD"] = result["月销量标准差"] / np.sqrt(30)  # 月 → 日的标准差转换

    # 安全库存 = Z × 日标准差 × √补货周期
    # round(0).astype(int): 四舍五入到整数，安全库存必须是整数件
    result["安全库存"] = (
        result["日均MAD"] * np.sqrt(config.REPLENISHMENT_CYCLE) * z_factor
    ).round(0).astype(int)                 # 取整

    return result[["SKU", "月均销量", "月销量标准差", "安全库存"]]


def calculate_cycle_stock(
    df_monthly: pd.DataFrame,
    replenishment_cycle: int = None,       # Optional, 不传就用 config 里的默认值
) -> pd.DataFrame:
    """
    计算周转库存 —— "补货周期内正常消耗的量"

    公式：
      日均需求 = 月均销量 / 30
      周转库存 = 日均需求 × 补货周期 / 2

    为什么要除以 2？
      假设库存从"满"到"空"线性消耗，平均库存 = 峰值的一半。
      这个简化的"锯齿模型"是 EOQ 理论的推论。

    Args:
        df_monthly: 月度销量 DataFrame
        replenishment_cycle: 补货周期（天），None 则取 config 默认 15 天

    Returns:
        DataFrame: SKU, 日均需求, 周转库存
    """
    if replenishment_cycle is None:        # 没传就用全局配置
        replenishment_cycle = config.REPLENISHMENT_CYCLE  # 默认 15 天

    # 计算每个 SKU 的月均销量
    result = df_monthly.groupby("SKU")["实际销量"].mean().reset_index()  # 按月均
    result.columns = ["SKU", "月均销量"]    # 重命名列

    result["日均需求"] = (result["月均销量"] / 30).round(1)  # 月均 ÷ 30 = 日均，保留1位小数
    # 周转库存 = 日均需求 × 补货周期 / 2，取整
    result["周转库存"] = (result["日均需求"] * replenishment_cycle / 2).round(0).astype(int)

    return result[["SKU", "日均需求", "周转库存"]]  # 返回需要的三列


def classify_abc(
    df_monthly: pd.DataFrame,
) -> pd.DataFrame:
    """
    ABC 分类 —— 按"销量金额贡献"从高到低划分

    分类标准（经典的 70/20/10 帕累托原则）：
      A 类: 累计销量占比 0~70%   → 最重要的少数（重点管理）
      B 类: 累计销量占比 70~90%  → 中等重要
      C 类: 累计销量占比 90~100% → 长尾产品（简化管理）

    注意：这里按"销量"而非"销售额"划分（简化版），
    要改为按金额只需在 groupby 时用 销量×单价。

    Args:
        df_monthly: 月度销量 DataFrame

    Returns:
        DataFrame: SKU, ABC分类
    """
    # 计算每个 SKU 的总销量（整个时间范围内的）
    total_sales = df_monthly.groupby("SKU")["实际销量"].sum().reset_index()  # 按 SKU 汇总总销量
    total_sales = total_sales.sort_values("实际销量", ascending=False)       # 从大到小排序

    # cumsum() = 累计求和 → 除以总和 = 累计占比
    total_sales["累计占比"] = total_sales["实际销量"].cumsum() / total_sales["实际销量"].sum()

    # apply + lambda：根据累计占比划分类别
    total_sales["ABC分类"] = total_sales["累计占比"].apply(
        lambda x: "A" if x <= 0.70 else ("B" if x <= 0.90 else "C")  # 三元嵌套判断
    )
    return total_sales[["SKU", "ABC分类"]]   # 只返回 SKU + 分类


def classify_xyz(
    df_monthly: pd.DataFrame,
) -> pd.DataFrame:
    """
    XYZ 分类 —— 按"需求波动程度"划分

    分类标准（变异系数 CV = 标准差 / 均值）：
      X 类: CV ≤ 0.2    → 需求非常稳定，容易预测
      Y 类: CV 0.2~0.5  → 需求有一定波动
      Z 类: CV > 0.5     → 需求波动剧烈，难以预测

    ABC + XYZ 组合策略示例：
      AX: 高价值+稳定 → 重点管理，JIT 补货
      AZ: 高价值+波动 → 重点管理 + 高安全库存
      CX: 低价值+稳定 → 自动化管理，定期补货
      CZ: 低价值+波动 → 考虑是否淘汰

    Args:
        df_monthly: 月度销量 DataFrame

    Returns:
        DataFrame: SKU, XYZ分类
    """
    # 计算每个 SKU 的均值和标准差（一次性 agg）
    stats = df_monthly.groupby("SKU")["实际销量"].agg(["mean", "std"]).reset_index()
    stats["CV"] = stats["std"] / stats["mean"]  # 变异系数 CV = 标准差/均值（无量纲，跨 SKU 可比）
    stats["CV"] = stats["CV"].fillna(0)          # 如果只有一个月的销量 std=NaN，填0（视为稳定）

    # 按 CV 阈值分类
    stats["XYZ分类"] = stats["CV"].apply(
        lambda x: "X" if x <= 0.2 else ("Y" if x <= 0.5 else "Z")
    )
    return stats[["SKU", "XYZ分类"]]  # 只返回 SKU + 分类


def run_inventory_plan(
    df_monthly: pd.DataFrame,              # 月度实际销量数据
    z_factor: float = None,                # 安全因子（None = 用全局默认值）
) -> pd.DataFrame:
    """
    库存计划主函数 —— "一键运行"

    串联四个子模块：
      安全库存 → 周转库存 → ABC分类 → XYZ分类
      → 合并 → 计算目标库存 → 输出标准格式的 DataFrame

    Args:
        df_monthly: 月度销量 DataFrame（列: SKU, 月份, 实际销量）
        z_factor: 安全因子（可选，覆盖全局配置）

    Returns:
        标准 InventoryPlanResult DataFrame:
          SKU, 日均需求, 安全库存, 周转库存, 目标库存, ABC分类, XYZ分类
    """
    ip = InventoryPlanResult()             # 获取列名常量（用于重命名 + 选列）

    # 依次调用四个子模块
    safety = calculate_safety_stock(df_monthly, z_factor)  # 子模块1：安全库存
    cycle = calculate_cycle_stock(df_monthly)              # 子模块2：周转库存
    abc = classify_abc(df_monthly)                         # 子模块3：ABC 分类
    xyz = classify_xyz(df_monthly)                         # 子模块4：XYZ 分类

    # 四张子表按 SKU 链式合并（相当于 SQL 的多次 INNER JOIN）
    result = safety.merge(cycle, on="SKU").merge(abc, on="SKU").merge(xyz, on="SKU")

    # 目标库存 = 安全库存 + 周转库存（经典公式）
    result[ip.TARGET_INVENTORY] = result["安全库存"] + result["周转库存"]

    # 重命名列，匹配 InventoryPlanResult 的定义
    result = result.rename(columns={
        "日均需求": ip.AVG_DAILY_DEMAND,   # → "日均需求"
        "安全库存": ip.SAFETY_STOCK,       # → "安全库存"
        "周转库存": ip.CYCLE_STOCK,        # → "周转库存"
        "目标库存": ip.TARGET_INVENTORY,   # → "目标库存"
        "ABC分类": ip.ABC_CLASS,           # → "ABC分类"
        "XYZ分类": ip.XYZ_CLASS,           # → "XYZ分类"
    })

    # 按 Schema 定义的顺序选列输出
    return result[[ip.SKU, ip.AVG_DAILY_DEMAND, ip.SAFETY_STOCK,
                    ip.CYCLE_STOCK, ip.TARGET_INVENTORY,
                    ip.ABC_CLASS, ip.XYZ_CLASS]]
