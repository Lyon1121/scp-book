"""
预测准确率指标 —— 需求预测"打分卡"

供应链中常用的四个预测准确率指标，各有侧重：
  MAPE  → 百分比误差（跨产品可比）
  MAD   → 绝对偏差（直观，保留量纲）
  RMSE  → 对大误差惩罚更重（关注极端偏差）
  Bias  → 系统性偏差方向（是老是高估还是低估？）

一个完整的预测评估应同时看这四个指标，
只盯一个容易得出片面的结论。

所有函数约定：
  输入: actual (实际值), forecast (预测值)，两个等长的 numpy 数组
  输出: float（MAPE 已 ×100 转百分比）
"""
import numpy as np                                      # numpy 提供向量化计算（避免 Python 慢循环）


def mape(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    MAPE — 平均绝对百分比误差（Mean Absolute Percentage Error）

    公式：
      MAPE = mean(|实际 - 预测| / 实际) × 100%

    解读：
      10% = 平均预测偏差在实际值的 10% 以内
      这是供应链最常用的指标，因为百分比可以跨 SKU 比较
      （卖 100 件的 SKU 差 10 件 = 10%，卖 10000 件的差 1000 件也 = 10%）

    注意：
      如果实际销量为 0（没人买），分母为 0 无法计算，
      我们用 mask 过滤掉这些记录。

    Args:
        actual: 实际销量数组
        forecast: 预测销量数组（必须与 actual 等长）

    Returns:
        float: MAPE 百分比值（如 9.46 表示 9.46% 的误差），无有效数据时返回 NaN
    """
    mask = actual != 0                                   # 布尔数组：标记实际值 ≠ 0 的位置
    if mask.sum() == 0:                                  # 如果所有实际值都是 0
        return np.nan                                    #   无法计算百分比，返回 NaN
    # 向量化计算：只对 actual ≠ 0 的记录求 |(A-F)/A| 的均值，再 ×100
    return np.mean(np.abs((actual[mask] - forecast[mask]) / actual[mask])) * 100


def mad(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    MAD — 平均绝对偏差（Mean Absolute Deviation）

    公式：
      MAD = mean(|实际 - 预测|)

    解读：
      保留了原始量纲（件），比百分比更直观。
      例如 MAD = 500 表示平均每次预测与实际差 500 件。

    Args:
        actual: 实际销量数组
        forecast: 预测销量数组

    Returns:
        float: 平均绝对偏差（保留原始单位）
    """
    return np.mean(np.abs(actual - forecast))            # |差值| 的平均值


def rmse(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    RMSE — 均方根误差（Root Mean Square Error）

    公式：
      RMSE = sqrt(mean((实际 - 预测)²))

    解读：
      RMSE 和 MAD 类似但有一个关键区别 —— RMSE 对"大偏差"惩罚更重
      （因为偏差先平方再开根），所以 RMSE 比 MAD 更"敏感"。

      如果 RMSE >> MAD，说明预测中存在一些非常大的偏差（偶发的大失误）。

    Args:
        actual: 实际销量数组
        forecast: 预测销量数组

    Returns:
        float: 均方根误差
    """
    return np.sqrt(np.mean((actual - forecast) ** 2))    # 平方 → 均值 → 开根


def bias(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    Bias — 预测偏差（系统性偏差方向）

    公式：
      Bias = mean(预测 - 实际)

    解读：
      Bias > 0  → 预测系统性高估（销售人员乐观偏置）
      Bias < 0  → 预测系统性低估（销售人员保守）
      Bias ≈ 0  → 预测整体无偏（但可能有波动）

    这是唯一一个"不取绝对值"的指标，
    因为它关心的不是"错多少"，而是"往哪个方向错"。

    Args:
        actual: 实际销量数组
        forecast: 预测销量数组

    Returns:
        float: 偏差值（正 = 高估，负 = 低估）
    """
    return np.mean(forecast - actual)                    # 不取绝对值！保留正负号


def calculate_all_metrics(actual: np.ndarray, forecast: np.ndarray) -> dict:
    """
    一键计算所有四个指标，返回汇总字典

    适用场景：
      你想快速看一下预测的整体表现，不需要分别调四个函数。

    Args:
        actual: 实际销量数组
        forecast: 预测销量数组

    Returns:
        dict: {"MAPE (%)": 9.46, "MAD": 456.2, "RMSE": 520.1, "Bias": -30.5}
    """
    return {
        "MAPE (%)": round(mape(actual, forecast), 2),    # 百分比误差，保留 2 位
        "MAD": round(mad(actual, forecast), 2),          # 绝对偏差
        "RMSE": round(rmse(actual, forecast), 2),        # 均方根误差
        "Bias": round(bias(actual, forecast), 2),        # 系统性偏差
    }
