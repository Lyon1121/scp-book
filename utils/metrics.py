"""
预测准确率指标

所有函数输入均为两个等长 Series/array:
    actual: 实际值
    forecast: 预测值
输出: float（百分比已乘100）
"""
import numpy as np


def mape(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    平均绝对百分比误差 MAPE (%)
    MAPE = mean(|(actual - forecast) / actual|) × 100
    """
    mask = actual != 0
    if mask.sum() == 0:
        return np.nan
    return np.mean(np.abs((actual[mask] - forecast[mask]) / actual[mask])) * 100


def mad(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    平均绝对偏差 MAD
    MAD = mean(|actual - forecast|)
    """
    return np.mean(np.abs(actual - forecast))


def rmse(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    均方根误差 RMSE
    RMSE = sqrt(mean((actual - forecast)^2))
    """
    return np.sqrt(np.mean((actual - forecast) ** 2))


def bias(actual: np.ndarray, forecast: np.ndarray) -> float:
    """
    预测偏差 Bias
    Bias = mean(forecast - actual)
    正值 = 高估, 负值 = 低估
    """
    return np.mean(forecast - actual)


def calculate_all_metrics(actual: np.ndarray, forecast: np.ndarray) -> dict:
    """
    一次性计算所有指标

    Returns:
        dict: {"MAPE": ..., "MAD": ..., "RMSE": ..., "Bias": ...}
    """
    return {
        "MAPE (%)": round(mape(actual, forecast), 2),
        "MAD": round(mad(actual, forecast), 2),
        "RMSE": round(rmse(actual, forecast), 2),
        "Bias": round(bias(actual, forecast), 2),
    }
