"""
需求预测模块 —— 双轨制需求预测

"双轨"指两套预测体系同时运行、互相校验：
  轨道1（人工）: 销售人员根据市场经验每月填写的预测
  轨道2（统计）: 基于历史销量数据的数学模型（移动平均 / 指数平滑）

核心业务逻辑：
  1. 日级销量数据 → 聚合为月度数据（因为人工预测是月度的）
  2. 历史时期：实际销量 vs 人工预测 → 计算"达成率"（评估销售人员预测能力）
  3. 未来时期：统计预测 vs 人工预测 → 计算"偏差"（对比两种预测的差异）

为什么叫"达成率"而不是"准确率"？
  因为人工预测先于实际发生，实际围绕预测波动，
  "达成率"更能体现"销售计划完成度"的业务含义。

技术架构：
  BaseForecaster (抽象基类)
    ├── MovingAverageForecaster (简单移动平均)
    └── SimpleExponentialSmoothingForecaster (一次指数平滑)
  通过工厂函数 get_forecaster() 实现"插拔式"切换，
  后续加新方法只需：写一个子类 + 在工厂里注册。
"""
import pandas as pd                                     # 数据分析核心库
import numpy as np                                      # 数值计算（数组、数学运算）
from abc import ABC, abstractmethod                     # ABC = 抽象基类，用于定义接口规范
from typing import Optional                             # Optional 表示"可选类型"（可以是 None）
from data.schemas import SalesInput, ManualForecastInput, ForecastCompareResult  # 列名常量
from utils.metrics import mape, mad                      # 预测准确率指标函数


# ============================================================
# 数据准备：日销量 → 月度聚合
# ============================================================
def aggregate_to_monthly(df_sales: pd.DataFrame) -> pd.DataFrame:
    """
    将「日级销量数据」按 SKU + 月份聚合为「月度销量」

    为什么需要这一步？
      历史销量 CSV 是日级的（每天每个 SKU 每个渠道一条记录），
      但人工预测是月度的（每月每个 SKU 一个数字），
      统计预测模型也按月训练更合理。
      所以第一步就是把日数据拍平成月数据。

    聚合方式：按 (SKU, 月份) 分组，对当日销量做 SUM。

    Args:
        df_sales: 日级销量 DataFrame，列名参考 SalesInput
                  必须包含: SKU, 日期(如2024-01-15), 销量, 渠道

    Returns:
        月度聚合 DataFrame，列: SKU, 月份(如2024-01), 实际销量

    Example:
        输入:
          SKU001  2024-01-01  100  亚马逊
          SKU001  2024-01-02  120  亚马逊
          SKU001  2024-01-01   50  独立站
        输出:
          SKU001  2024-01  270
    """
    si = SalesInput()                                    # 获取销量 CSV 的列名常量
    df = df_sales.copy()                                 # 复制一份，避免修改原始数据
    # 日期格式兼容："2024/1/1" 或 "2024-01-01" → 统一转为 YYYY-MM 格式匹配 Sales_forecasting.csv
    df["月份"] = pd.to_datetime(df[si.DATE]).dt.strftime("%Y-%m")  # e.g. "2024-01"
    monthly = df.groupby([si.SKU, "月份"])[si.SALES].sum().reset_index()  # 按 (SKU, 月份) 分组求销量和
    monthly.rename(columns={si.SALES: "实际销量"}, inplace=True)  # 列名"销量" → "实际销量"，语义更清晰
    return monthly                                       # 返回月度数据


# ============================================================
# 统计预测器 —— 抽象基类（接口规范）
# ============================================================
class BaseForecaster(ABC):
    """
    统计预测器的抽象基类

    定义了两个"必须实现"的抽象方法（fit / predict）和一个"可以直接用"的评估方法（evaluate）。

    所有预测方法（移动平均、指数平滑、未来的 ARIMA 等）都继承这个类，
    这样外部调用方不需要关心具体用了什么算法，统一调 fit() 和 predict() 即可。

    这就是"策略模式"（Strategy Pattern）在供应链预测中的落地。
    """

    def __init__(self, name: str = "Base"):
        """
        初始化预测器

        Args:
            name: 预测器的显示名称，会出现在结果报告中
        """
        self.name = name                                 # 预测器名称，如"移动平均(窗口=3)"
        self._fitted = False                             # 标记是否已训练（防止未训练就预测）

    @abstractmethod                                      # 抽象方法：子类必须实现
    def fit(self, series: np.ndarray):
        """
        用历史月度销量数据"训练"模型

        不同方法的 fit 逻辑完全不同：
          移动平均：记住最后 N 个月的值
          指数平滑：迭代计算平滑值，记住最后一个
          ARIMA：估计 p,d,q 参数

        Args:
            series: 历史月度销量数组，如 [4500, 5200, 4800, ...]
        """
        ...                                              # 抽象方法不需要写实现体

    @abstractmethod                                      # 抽象方法：子类必须实现
    def predict(self, steps: int) -> np.ndarray:
        """
        预测未来 steps 个月的销量

        必须先调用 fit() 才能调 predict()。

        Args:
            steps: 预测未来多少个月

        Returns:
            长度为 steps 的 numpy 数组，每个元素是当月的预测销量
        """
        ...

    def evaluate(self, actual: np.ndarray, forecast: np.ndarray) -> dict:
        """
        评估预测准确率（所有子类通用，不需要重写）

        用 MAPE 和 MAD 两个指标量化预测表现：
          MAPE（百分比误差）：跨 SKU 可比较
          MAD（绝对偏差）：保留原始量纲，直观

        Args:
            actual: 实际销量数组
            forecast: 预测销量数组（必须与 actual 等长）

        Returns:
            dict: {"方法": ..., "MAPE (%)": ..., "MAD": ...}
        """
        return {
            "方法": self.name,
            "MAPE (%)": round(mape(actual, forecast), 2),   # 调用 utils/metrics.py 中的 mape 函数
            "MAD": round(mad(actual, forecast), 2),         # 调用 utils/metrics.py 中的 mad 函数
        }


# ============================================================
# 统计预测器实现 1：简单移动平均
# ============================================================
class MovingAverageForecaster(BaseForecaster):
    """
    简单移动平均预测器

    原理：
      取最近 window 个月销量的平均值，作为未来所有月份的预测值。

    优点：直观、可解释、计算快
    缺点：无法反映趋势和季节性（未来每个月的预测值都一样）

    适用场景：
      需求相对平稳的 SKU（XYZ 分类中的 X 类）

    公式：
      预测值 = (上月销量 + 上上月销量 + ... + 上N月销量) / N

    Example:
      历史：[100, 120, 110, 130, 140]，窗口=3
      取最后3个 → [110, 130, 140]
      平均值 = (110+130+140)/3 = 126.7
      未来6个月全部预测为 126.7
    """

    def __init__(self, window: int = 3):
        """
        Args:
            window: 移动平均的窗口大小（取最近几个月），默认 3 个月
        """
        super().__init__(name=f"移动平均(窗口={window})")  # 调用父类构造函数，设置名称
        self.window = window                              # 保存窗口大小
        self._last_values = None                          # 存储最后 window 个月的值（fit 时赋值）

    def fit(self, series: np.ndarray):
        """
        "训练"移动平均模型 —— 只需记住最后 window 个月的值

        Args:
            series: 历史月度销量数组
        """
        self._last_values = series[-self.window:]         # 取数组最后 window 个元素
        self._fitted = True                               # 标记已训练

    def predict(self, steps: int) -> np.ndarray:
        """
        用最后 window 个月的平均值预测未来 steps 个月

        Args:
            steps: 预测步数（月数）

        Returns:
            长度为 steps 的数组，每个元素都是同一个平均值
        """
        if not self._fitted:                              # 安全检查：没训练就预测 → 报错
            raise RuntimeError("请先调用 fit()")
        avg = np.mean(self._last_values)                  # 计算最后 window 个月的平均值
        return np.full(steps, avg)                        # 用 np.full 生成长度为 steps、全是 avg 的数组


# ============================================================
# 统计预测器实现 2：一次指数平滑
# ============================================================
class SimpleExponentialSmoothingForecaster(BaseForecaster):
    """
    一次指数平滑预测器（Simple Exponential Smoothing, SES）

    原理：
      越近期的数据权重越大（指数衰减权重），用一个平滑系数 α 控制衰减速度。

    迭代公式：
      S_t = α × Y_t + (1-α) × S_{t-1}
      其中 S_t = 第 t 期的平滑值，Y_t = 第 t 期的实际值，α = 平滑系数

    参数解读：
      α 接近 1：对近期变化非常敏感（像在追着数据跑）
      α 接近 0：非常平滑，变化迟缓（像长期平均）

    与移动平均的区别：
      移动平均：最后 N 个月权重相同，N 个月前的权重为 0（硬截断）
      指数平滑：权重指数衰减，没有硬截断，更"优雅"

    适用场景：
      有轻微趋势但无强季节性的 SKU（XYZ 分类中的 Y 类）
    """

    def __init__(self, alpha: float = 0.3):
        """
        Args:
            alpha: 平滑系数，0~1 之间。默认 0.3（偏平滑）
        """
        super().__init__(name=f"指数平滑(α={alpha})")     # 设置名称
        self.alpha = alpha                               # 保存平滑系数
        self._last_smoothed = None                       # 存储最后一次平滑值（fit 时计算）

    def fit(self, series: np.ndarray):
        """
        用整个历史序列做指数平滑迭代，取最后一个平滑值

        迭代过程：
          从第1个值开始，逐月应用公式 S_t = α×Y_t + (1-α)×S_{t-1}
          遍历完整个序列后，self._last_smoothed 就是最新的平滑值

        Args:
            series: 历史月度销量数组
        """
        smoothed = series[0]                             # 初始平滑值 = 第一个月的实际值
        for val in series[1:]:                           # 从第二个月开始迭代
            # 核心公式：新平滑值 = α×当前实际 + (1-α)×上期平滑值
            smoothed = self.alpha * val + (1 - self.alpha) * smoothed
        self._last_smoothed = smoothed                   # 保存最终的平滑值
        self._fitted = True                              # 标记已训练

    def predict(self, steps: int) -> np.ndarray:
        """
        对一次指数平滑而言，未来所有月份的预测值 = 最新的平滑值

        这是一个"朴素"预测（naive forecast），没有趋势项，
        所以未来每个月预测值都一样。

        Args:
            steps: 预测步数

        Returns:
            长度为 steps 的数组，每项都是最后平滑值
        """
        if not self._fitted:
            raise RuntimeError("请先调用 fit()")
        return np.full(steps, self._last_smoothed)       # 未来全是同一个平滑值


# ============================================================
# 工厂函数：预测方法的"开关面板"
# ============================================================
def get_forecaster(method: str, **kwargs) -> BaseForecaster:
    """
    根据方法名称 + 参数，返回对应的预测器实例

    这就是"工厂模式"（Factory Pattern）：
      调用方不需要知道 MovingAverageForecaster 这个类名，
      只需要传字符串 "moving_average" 就能拿到实例。

    好处：
      1. 新增预测方法时，只需在这里加一个 if 分支
      2. Streamlit 下拉菜单直接绑定 method 字符串
      3. 配置文件中可以写方法名而不是类名

    Args:
        method: 预测方法标识符
                "moving_average"      → 移动平均
                "exponential_smoothing" → 指数平滑
        **kwargs: 传递给预测器构造函数的参数
                  对移动平均: window=3
                  对指数平滑: alpha=0.3

    Returns:
        BaseForecaster 的子类实例

    Raises:
        ValueError: 传入了不支持的方法名
    """
    if method == "moving_average":                       # 方法1：移动平均
        return MovingAverageForecaster(window=kwargs.get("window", 3))  # 取 window 参数，默认 3
    elif method == "exponential_smoothing":               # 方法2：指数平滑
        return SimpleExponentialSmoothingForecaster(alpha=kwargs.get("alpha", 0.3))  # 取 alpha 参数，默认 0.3
    else:                                                # 不支持的方法 → 报错并提示可用选项
        raise ValueError(f"未知预测方法: {method}，可选: moving_average, exponential_smoothing")


# ============================================================
# 双轨对比：历史时期
# ============================================================
def compare_historical(
    df_sales: pd.DataFrame,
    df_manual: pd.DataFrame,
) -> pd.DataFrame:
    """
    历史对比：实际销量 vs 销售人员人工预测 → 计算达成率

    业务含义：
      销售人员每个月会填一个"我预测这个月卖多少"。
      月底看实际数据，算一下：实际 / 预测 = 达成率。
      达成率 > 100% → 销售超预期（好事/预测保守）
      达成率 < 100% → 未达预期（需要关注）

    处理流程：
      1. 把日销量拍平成月度实际销量
      2. 从人工预测 CSV 中筛选出"类型=历史"的行
      3. 按 (SKU, 月份) 合并两张表
      4. 计算达成率 = 实际销量 / 人工预测量 × 100%
      5. 统计预测列留空（历史时期主要看人工预测表现）

    Args:
        df_sales: 日级销量 DataFrame
        df_manual: 月度人工预测 DataFrame（包含"历史"和"未来"两部分）

    Returns:
        DataFrame 列: SKU, 月份, 实际销量, 人工预测量, 统计预测量(NaN), 达成率_人工, 偏差_统计vs人工(NaN)
    """
    mf = ManualForecastInput()                           # 获取人工预测 CSV 的列名常量
    fc = ForecastCompareResult()                         # 获取对比结果表的列名常量

    # 步骤1: 日销量 → 月度实际销量
    monthly_actual = aggregate_to_monthly(df_sales)      # 调用前面的聚合函数

    # 步骤2: 从人工预测中筛选"类型=历史"的行，只取需要的那三列
    historical_manual = df_manual[df_manual[mf.FORECAST_TYPE] == "历史"][  # 布尔索引：只保留"历史"行
        [mf.SKU, mf.PERIOD, mf.FORECAST]                 # 只取 SKU、月份、人工预测量 三列
    ].copy()                                             # .copy() 防止 SettingWithCopyWarning

    # 步骤3: 合并实际销量和人工预测（按 SKU + 月份 对齐）
    merged = monthly_actual.merge(                       # pandas 的 merge 相当于 SQL 的 JOIN
        historical_manual,                               # 左表：月度实际销量
        left_on=["SKU", "月份"],                         # 左表关联键
        right_on=[mf.SKU, mf.PERIOD],                    # 右表关联键
        how="inner"                                      # 内连接：只保留两边都有的记录
    )

    # 步骤4: 计算达成率
    merged = merged.rename(columns={                     # 重命名列，匹配目标 Schema
        mf.FORECAST: fc.MANUAL_FORECAST,                 # "人工预测量" → 统一列名
        "实际销量": fc.ACTUAL,                            # "实际销量" → 统一列名
    })

    # np.where(条件, 真值, 假值)：向量化的 if-else
    merged[fc.ACHIEVEMENT_RATE] = np.where(               # 达成率 = 实际 / 人工 × 100
        merged[fc.MANUAL_FORECAST] > 0,                   # 条件：人工预测 > 0（避免除零）
        (merged[fc.ACTUAL] / merged[fc.MANUAL_FORECAST] * 100).round(1),  # 真：计算百分比，保留1位小数
        np.nan                                            # 假：人工预测为0时，达成率无意义，填 NaN
    )

    # 步骤5: 统计预测和偏差列暂时留空（历史部分只看人工 vs 实际）
    merged[fc.STAT_FORECAST] = np.nan                    # 统计预测量 = NaN
    merged[fc.STAT_DEVIATION] = np.nan                   # 偏差 = NaN

    # 按目标 Schema 选取列，确保输出格式统一
    result = merged[[fc.SKU, fc.PERIOD, fc.ACTUAL, fc.MANUAL_FORECAST,
                      fc.STAT_FORECAST, fc.ACHIEVEMENT_RATE, fc.STAT_DEVIATION]]
    result.columns = [fc.SKU, fc.PERIOD, fc.ACTUAL, fc.MANUAL_FORECAST,  # 显式重设列名
                      fc.STAT_FORECAST, fc.ACHIEVEMENT_RATE, fc.STAT_DEVIATION]
    return result                                        # 返回历史对比表


# ============================================================
# 双轨对比：未来时期
# ============================================================
def compare_future(
    df_manual: pd.DataFrame,
    forecaster: BaseForecaster,
    historical_monthly: pd.DataFrame,
) -> pd.DataFrame:
    """
    未来对比：销售人员人工预测 vs 统计模型预测 → 计算偏差

    业务含义：
      未来的销量还没发生，没法算"达成率"。
      但我们有两套预测：销售人员的直觉 vs 统计模型的冷冰冰的数字。
      把它们放在一起对比，计算偏差：
        偏差 = (统计预测 - 人工预测) / 人工预测 × 100%

      偏差 > 0：统计模型比销售人员乐观
      偏差 < 0：统计模型比销售人员保守

    处理流程：
      1. 从人工预测 CSV 中筛选"类型=未来"的行
      2. 对每个 SKU 单独处理：
         a. 用该 SKU 的历史月度数据训练统计模型
         b. 用统计模型预测未来 N 个月
         c. 逐月计算偏差

    为什么要按 SKU 分别训练？
      不同 SKU 的销量量级、趋势、波动特征完全不同，
      用一个模型预测所有 SKU 会得到非常差的结果。

    Args:
        df_manual: 月度人工预测 DataFrame
        forecaster: 统计预测器实例（已通过工厂函数创建）
        historical_monthly: 历史月度实际销量（用于训练）

    Returns:
        DataFrame 列: SKU, 月份, 实际销量(NaN), 人工预测量, 统计预测量, 达成率_人工(NaN), 偏差_统计vs人工
    """
    mf = ManualForecastInput()                           # 人工预测 CSV 列名常量
    fc = ForecastCompareResult()                         # 对比结果表列名常量

    # 步骤1: 筛选未来部分的预测，只取需要的那三列
    future_manual = df_manual[df_manual[mf.FORECAST_TYPE] == "未来"][  # 只保留"未来"行
        [mf.SKU, mf.PERIOD, mf.FORECAST]                 # 只取三列
    ].copy()

    results = []                                         # 用列表收集结果行，最后一次性转 DataFrame（高效）
    for sku in future_manual[mf.SKU].unique():           # 遍历每个 SKU（unique() 去重）
        # 该 SKU 的未来预测，按月份排序
        sku_manual = future_manual[future_manual[mf.SKU] == sku].sort_values(mf.PERIOD)
        periods = sku_manual[mf.PERIOD].values            # 未来月份列表，如 ["2026-01", "2026-02", ...]
        manual_values = sku_manual[mf.FORECAST].values    # 对应的人工预测值数组
        steps = len(periods)                              # 预测步数 = 未来月份数

        # 该 SKU 的历史月度实际销量（用于训练统计模型）
        sku_history = historical_monthly[historical_monthly["SKU"] == sku]["实际销量"].values
        if len(sku_history) == 0:                         # 没有历史数据 → 跳过这个 SKU
            continue

        forecaster.fit(sku_history)                      # 用该 SKU 的历史数据训练统计模型
        stat_forecast = forecaster.predict(steps)          # 预测未来 steps 个月

        # 逐月构建结果行
        for i, period in enumerate(periods):              # enumerate 同时获取索引 i 和值 period
            manual_fc = manual_values[i]                  # 本月人工预测
            stat_fc = stat_forecast[i]                    # 本月统计预测
            # 偏差公式：(统计 - 人工) / 人工 × 100，如果人工=0 则偏差=0
            deviation = ((stat_fc - manual_fc) / manual_fc * 100) if manual_fc > 0 else 0

            results.append({                             # 构建一行结果
                fc.SKU: sku,                             # SKU 编码
                fc.PERIOD: period,                       # 月份
                fc.ACTUAL: np.nan,                       # 未来没有实际值，填 NaN
                fc.MANUAL_FORECAST: manual_fc,           # 人工预测值
                fc.STAT_FORECAST: int(round(stat_fc)),    # 统计预测值（取整为整数）
                fc.ACHIEVEMENT_RATE: np.nan,              # 未来没有达成率，填 NaN
                fc.STAT_DEVIATION: round(deviation, 1),   # 偏差百分比，保留1位小数
            })

    return pd.DataFrame(results)                         # 列表 → DataFrame，一次性构建


# ============================================================
# 主入口：一键运行双轨需求预测
# ============================================================
def run_dual_forecast(
    df_sales: pd.DataFrame,
    df_manual: pd.DataFrame,
    method: str = "moving_average",
    **kwargs,
) -> dict:
    """
    双轨需求预测的"一键启动"函数

    这是外部调用的唯一入口（pipeline.py 和 app.py 都只调这个函数）。

    内部逻辑：
      1. 跑历史对比 → 产出"达成率报表"
      2. 跑未来对比 → 产出"偏差分析报表"
      3. 从两张报表中提取关键指标 → 产出"汇总摘要"

    Args:
        df_sales: 日级销量 DataFrame
        df_manual: 月度人工预测 DataFrame
        method: 统计预测方法，"moving_average" 或 "exponential_smoothing"
        **kwargs: 传递给 get_forecaster 的参数

    Returns:
        dict:
          - "historical_compare": DataFrame — 历史对比明细表
          - "future_compare": DataFrame — 未来对比明细表
          - "summary": dict — 汇总指标（达成率均值、MAPE、偏差均值等）
    """
    # 步骤1: 历史对比（实际 vs 人工 → 达成率）
    historical = compare_historical(df_sales, df_manual)

    # 步骤2: 准备历史月度数据（统计模型训练用）
    monthly_actual = aggregate_to_monthly(df_sales)      # 日 → 月

    # 步骤3: 通过工厂函数创建预测器实例
    forecaster = get_forecaster(method, **kwargs)

    # 步骤4: 未来对比（统计 vs 人工 → 偏差）
    future = compare_future(df_manual, forecaster, monthly_actual)

    # 步骤5: 生成汇总指标
    summary = {}                                         # 汇总字典，Streamlit 页面上方四个指标卡的数据来源
    if not historical.empty:                             # 历史表不为空才计算
        valid = historical["达成率_人工"].dropna()        # 去掉 NaN（人工预测为0的记录）
        summary["历史达成率_平均(%)"] = round(valid.mean(), 1)    # 平均达成率
        summary["历史达成率_最高(%)"] = round(valid.max(), 1)     # 最高达成率
        summary["历史达成率_最低(%)"] = round(valid.min(), 1)     # 最低达成率
        # MAPE：人工预测对实际销量的平均百分比误差
        summary["历史MAPE_人工vs实际(%)"] = round(
            mape(historical["实际销量"].values, historical["人工预测量"].values), 2
        )

    if not future.empty:                                 # 未来表不为空才计算
        valid_dev = future["偏差_统计vs人工"].dropna()    # 去掉 NaN
        summary["未来偏差_统计vs人工_平均(%)"] = round(valid_dev.mean(), 1)   # 平均偏差
        summary["未来偏差_统计vs人工_最大偏差(%)"] = round(valid_dev.abs().max(), 1)  # 最大绝对偏差
        summary["预测方法"] = forecaster.name              # 统计预测方法名称

    return {                                             # 返回三个部分的字典
        "historical_compare": historical,                # 历史对比详表
        "future_compare": future,                        # 未来对比详表
        "summary": summary,                              # 汇总指标
    }
