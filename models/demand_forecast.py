"""
需求预测模块 — 双轨制

轨道1: 销售人员月度人工预测
轨道2: 统计预测（移动平均 / 指数平滑）

输出:
  - 历史: 实际销量 vs 人工预测 → 达成率
  - 未来: 人工预测 vs 统计预测 → 偏差分析
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional
from data.schemas import SalesInput, ManualForecastInput, ForecastCompareResult
from utils.metrics import mape, mad


# ============================================================
# 数据准备
# ============================================================
def aggregate_to_monthly(df_sales: pd.DataFrame) -> pd.DataFrame:
    """
    将日销量聚合为月度销量

    Args:
        df_sales: 日级销量 DataFrame (列: SKU, 日期, 销量, 渠道)

    Returns:
        月度汇总 DataFrame (列: SKU, 月份, 实际销量)
    """
    si = SalesInput()
    df = df_sales.copy()
    df["月份"] = df[si.DATE].str[:7]  # "2024-01"
    monthly = df.groupby([si.SKU, "月份"])[si.SALES].sum().reset_index()
    monthly.rename(columns={si.SALES: "实际销量"}, inplace=True)
    return monthly


# ============================================================
# 基类: 统计预测器
# ============================================================
class BaseForecaster(ABC):
    """统计预测器抽象基类"""

    def __init__(self, name: str = "Base"):
        self.name = name
        self._fitted = False

    @abstractmethod
    def fit(self, series: np.ndarray):
        """用历史月度数据训练"""
        ...

    @abstractmethod
    def predict(self, steps: int) -> np.ndarray:
        """预测未来 steps 个月的销量"""
        ...

    def evaluate(self, actual: np.ndarray, forecast: np.ndarray) -> dict:
        """评估预测准确率"""
        return {
            "方法": self.name,
            "MAPE (%)": round(mape(actual, forecast), 2),
            "MAD": round(mad(actual, forecast), 2),
        }


# ============================================================
# 实现1: 移动平均
# ============================================================
class MovingAverageForecaster(BaseForecaster):
    """简单移动平均预测器"""

    def __init__(self, window: int = 3):
        super().__init__(name=f"移动平均(窗口={window})")
        self.window = window
        self._last_values = None

    def fit(self, series: np.ndarray):
        self._last_values = series[-self.window:]
        self._fitted = True

    def predict(self, steps: int) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("请先调用 fit()")
        avg = np.mean(self._last_values)
        return np.full(steps, avg)


# ============================================================
# 实现2: 一次指数平滑
# ============================================================
class SimpleExponentialSmoothingForecaster(BaseForecaster):
    """一次指数平滑预测器"""

    def __init__(self, alpha: float = 0.3):
        super().__init__(name=f"指数平滑(α={alpha})")
        self.alpha = alpha
        self._last_smoothed = None

    def fit(self, series: np.ndarray):
        # 用整个序列做指数平滑，取最后一个平滑值
        smoothed = series[0]
        for val in series[1:]:
            smoothed = self.alpha * val + (1 - self.alpha) * smoothed
        self._last_smoothed = smoothed
        self._fitted = True

    def predict(self, steps: int) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("请先调用 fit()")
        return np.full(steps, self._last_smoothed)


# ============================================================
# 工厂函数
# ============================================================
def get_forecaster(method: str, **kwargs) -> BaseForecaster:
    """
    获取预测器实例

    Args:
        method: "moving_average" | "exponential_smoothing"
        **kwargs: 传给预测器的参数 (window, alpha)
    """
    if method == "moving_average":
        return MovingAverageForecaster(window=kwargs.get("window", 3))
    elif method == "exponential_smoothing":
        return SimpleExponentialSmoothingForecaster(alpha=kwargs.get("alpha", 0.3))
    else:
        raise ValueError(f"未知预测方法: {method}，可选: moving_average, exponential_smoothing")


# ============================================================
# 双轨对比核心
# ============================================================
def compare_historical(
    df_sales: pd.DataFrame,
    df_manual: pd.DataFrame,
) -> pd.DataFrame:
    """
    历史对比: 实际销量 vs 销售人员人工预测 → 达成率

    Args:
        df_sales: 日级销量 (列: SKU, 日期, 销量, 渠道)
        df_manual: 月度人工预测 (列: SKU, 月份, 人工预测量, 类型)

    Returns:
        DataFrame with columns: SKU, 月份, 实际销量, 人工预测量, 达成率_人工
    """
    mf = ManualForecastInput()
    fc = ForecastCompareResult()

    # 1. 月度实际销量
    monthly_actual = aggregate_to_monthly(df_sales)

    # 2. 只取历史部分的人工预测
    historical_manual = df_manual[df_manual[mf.FORECAST_TYPE] == "历史"][
        [mf.SKU, mf.PERIOD, mf.FORECAST]
    ].copy()

    # 3. 合并
    merged = monthly_actual.merge(
        historical_manual,
        left_on=["SKU", "月份"],
        right_on=[mf.SKU, mf.PERIOD],
        how="inner"
    )

    # 4. 计算达成率
    merged = merged.rename(columns={
        mf.FORECAST: fc.MANUAL_FORECAST,
        "实际销量": fc.ACTUAL,
    })

    # 达成率 = 实际/人工预测 × 100
    merged[fc.ACHIEVEMENT_RATE] = np.where(
        merged[fc.MANUAL_FORECAST] > 0,
        (merged[fc.ACTUAL] / merged[fc.MANUAL_FORECAST] * 100).round(1),
        np.nan
    )

    # 统计预测列暂时为空
    merged[fc.STAT_FORECAST] = np.nan
    merged[fc.STAT_DEVIATION] = np.nan

    result = merged[[fc.SKU, fc.PERIOD, fc.ACTUAL, fc.MANUAL_FORECAST,
                      fc.STAT_FORECAST, fc.ACHIEVEMENT_RATE, fc.STAT_DEVIATION]]
    result.columns = [fc.SKU, fc.PERIOD, fc.ACTUAL, fc.MANUAL_FORECAST,
                      fc.STAT_FORECAST, fc.ACHIEVEMENT_RATE, fc.STAT_DEVIATION]
    return result


def compare_future(
    df_manual: pd.DataFrame,
    forecaster: BaseForecaster,
    historical_monthly: pd.DataFrame,
) -> pd.DataFrame:
    """
    未来对比: 销售人员人工预测 vs 统计模型预测 → 偏差

    Args:
        df_manual: 月度人工预测 (含"类型"="未来"的行)
        forecaster: 已训练的统计预测器
        historical_monthly: 历史月度实际销量 (用于训练统计模型)

    Returns:
        DataFrame with columns: SKU, 月份, 人工预测量, 统计预测量, 偏差_统计vs人工
    """
    mf = ManualForecastInput()
    fc = ForecastCompareResult()

    future_manual = df_manual[df_manual[mf.FORECAST_TYPE] == "未来"][
        [mf.SKU, mf.PERIOD, mf.FORECAST]
    ].copy()

    results = []
    for sku in future_manual[mf.SKU].unique():
        sku_manual = future_manual[future_manual[mf.SKU] == sku].sort_values(mf.PERIOD)
        periods = sku_manual[mf.PERIOD].values
        manual_values = sku_manual[mf.FORECAST].values
        steps = len(periods)

        # 训练统计模型（用该SKU的历史月度数据）
        sku_history = historical_monthly[historical_monthly["SKU"] == sku]["实际销量"].values
        if len(sku_history) == 0:
            continue

        forecaster.fit(sku_history)
        stat_forecast = forecaster.predict(steps)

        for i, period in enumerate(periods):
            manual_fc = manual_values[i]
            stat_fc = stat_forecast[i]
            deviation = ((stat_fc - manual_fc) / manual_fc * 100) if manual_fc > 0 else 0

            results.append({
                fc.SKU: sku,
                fc.PERIOD: period,
                fc.ACTUAL: np.nan,  # 未来无实际值
                fc.MANUAL_FORECAST: manual_fc,
                fc.STAT_FORECAST: int(round(stat_fc)),
                fc.ACHIEVEMENT_RATE: np.nan,
                fc.STAT_DEVIATION: round(deviation, 1),
            })

    return pd.DataFrame(results)


def run_dual_forecast(
    df_sales: pd.DataFrame,
    df_manual: pd.DataFrame,
    method: str = "moving_average",
    **kwargs,
) -> dict:
    """
    双轨需求预测主函数

    返回 dict:
      - historical_compare: 历史对比表 (实际 vs 人工 → 达成率)
      - future_compare: 未来对比表 (统计 vs 人工 → 偏差)
      - summary: 汇总指标
    """
    # 1. 历史对比
    historical = compare_historical(df_sales, df_manual)

    # 2. 获取月度历史数据用于训练
    monthly_actual = aggregate_to_monthly(df_sales)

    # 3. 选择预测器
    forecaster = get_forecaster(method, **kwargs)

    # 4. 未来对比 (为每个SKU单独训练+预测)
    future = compare_future(df_manual, forecaster, monthly_actual)

    # 5. 汇总指标
    summary = {}
    if not historical.empty:
        valid = historical["达成率_人工"].dropna()
        summary["历史达成率_平均(%)"] = round(valid.mean(), 1)
        summary["历史达成率_最高(%)"] = round(valid.max(), 1)
        summary["历史达成率_最低(%)"] = round(valid.min(), 1)
        summary["历史MAPE_人工vs实际(%)"] = round(
            mape(historical["实际销量"].values, historical["人工预测量"].values), 2
        )

    if not future.empty:
        valid_dev = future["偏差_统计vs人工"].dropna()
        summary["未来偏差_统计vs人工_平均(%)"] = round(valid_dev.mean(), 1)
        summary["未来偏差_统计vs人工_最大偏差(%)"] = round(valid_dev.abs().max(), 1)
        summary["预测方法"] = forecaster.name

    return {
        "historical_compare": historical,
        "future_compare": future,
        "summary": summary,
    }
