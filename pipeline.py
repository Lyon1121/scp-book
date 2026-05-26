"""
端到端 Pipeline —— 四模块联动编排

这就是整个供应链计划的"指挥中心"，负责：
  1. 加载三个 CSV 数据源
  2. 按顺序调用四个模块（需求预测 → 库存计划 → 供应计划 → 发货计划）
  3. 把上游模块的输出传递给下游模块
  4. 收集所有结果，打包成一个 dict 返回

外部调用方（app.py Streamlit 界面）只需要调一个函数：
  result = run_pipeline()
  → 拿到所有四张报表 + 汇总指标

数据流向：
  historical_sales.csv ──→ [需求预测] ──→ monthly (月度销量)
  manual_forecast.csv ──┘                        ↓
  current_inventory.csv ──→ [库存计划] ←──────────┘
                                   ↓
                            [供应计划] ←── current_inventory.csv
                                   ↓
                            [发货计划]
"""
import pandas as pd                                     # 数据分析（虽然本文件不直接用，模块间传递用）
from datetime import datetime                            # 日期处理
from pathlib import Path                                 # 路径处理

import config                                            # 全局配置（DATA_DIR 等）
from data.loader import load_csv                         # CSV 加载函数
from models.demand_forecast import run_dual_forecast, aggregate_to_monthly  # 需求预测
from models.inventory_plan import run_inventory_plan     # 库存计划
from models.supply_plan import run_supply_plan           # 供应计划
from models.shipment_plan import run_shipment_plan       # 发货计划


def run_pipeline(
    sales_path: str = None,               # 历史销量 CSV 路径（None = 用默认路径）
    manual_forecast_path: str = None,      # 人工预测 CSV 路径（None = 用默认路径）
    inventory_path: str = None,            # 当前库存 CSV 路径（None = 用默认路径）
    forecast_method: str = "moving_average",  # 统计预测方法（传给 demand_forecast）
    current_date: datetime = None,         # 当前日期（传给 supply_plan 算 ROD 日期）
    **forecast_kwargs,                     # 其他预测参数（如 window, alpha），透传
) -> dict:
    """
    一键运行完整供应链计划 Pipeline

    这是整个项目的"唯一入口函数"。
    不管是 Streamlit 界面、命令行测试、还是未来可能的 API，
    都通过这个函数获取四个模块的计算结果。

    流程（数据流）：
      Step 1: 加载三个 CSV 数据源
      Step 2: 需求预测（双轨对比）→ 产出: 历史达成率 + 未来偏差
      Step 3: 库存计划（安全库存 + ABC-XYZ）→ 产出: 目标库存
      Step 4: 供应计划（ROD 采购建议）→ 产出: 采购建议清单
      Step 5: 发货计划（海运/空运分配）→ 产出: 发货安排

    Args:
        sales_path: 历史销量 CSV，None 则用 sample_data/historical_sales.csv
        manual_forecast_path: 人工预测 CSV，None 则用 sample_data/manual_forecast.csv
        inventory_path: 库存 CSV，None 则用 sample_data/current_inventory.csv
        forecast_method: "moving_average" 或 "exponential_smoothing"
        current_date: "现在"的日期
        **forecast_kwargs: window、alpha 等传递到 get_forecaster()

    Returns:
        dict:
          "monthly"           : DataFrame — 月度汇总销量
          "demand_result"     : dict — {historical_compare, future_compare, summary}
          "inventory_plan"    : DataFrame — 库存计划表
          "supply_plan"       : DataFrame — 采购建议表
          "shipment_plan"     : DataFrame — 发货计划表
          "df_inventory"      : DataFrame — 原始库存数据
    """
    # ---- 路径处理：未指定就用默认 ----
    data_dir = config.DATA_DIR if sales_path is None else Path(sales_path).parent  # 确定数据目录
    if sales_path is None:                               # 没传就用默认
        sales_path = data_dir / "Sales_data.csv"
    if manual_forecast_path is None:
        manual_forecast_path = data_dir / "Sales_forecasting.csv"
    if inventory_path is None:
        inventory_path = data_dir / "SKU_Stock.csv"
    if current_date is None:                             # 没传日期就用系统当前时间
        current_date = datetime.now()

    # ---- Step 1: 加载三个数据源 ----
    df_sales = load_csv(str(sales_path))                 # 历史日销量（含渠道列）
    df_manual = load_csv(str(manual_forecast_path))      # 月度人工预测（含历史+未来）
    df_inventory = load_csv(str(inventory_path))          # 当前库存 + 在途

    # ---- Step 2: 需求预测（双轨对比） ----
    # 输出: {historical_compare, future_compare, summary}
    demand_result = run_dual_forecast(
        df_sales, df_manual,                             # 销量 + 人工预测
        method=forecast_method,                           # 统计方法
        **forecast_kwargs                                 # 额外参数（window / alpha）
    )

    # ---- Step 3: 库存计划 ----
    # 先把日销量聚合为月度（库存计划需要月度数据算安全库存）
    monthly = aggregate_to_monthly(df_sales)             # 日 → 月
    inventory_plan_df = run_inventory_plan(monthly)       # 产出: 日均需求、安全库存、周转库存、目标库存、ABC-XYZ

    # ---- Step 4: 供应计划（ROD 策略） ----
    # 输入: 当前库存 + 库存计划输出 → 输出: 采购建议
    supply_plan_df = run_supply_plan(
        df_inventory,                                    # 当前库存（含在途）
        inventory_plan_df,                               # 库存计划结果（含日均需求、目标库存）
        current_date=current_date                        # 基于哪个日期算 ROD
    )

    # ---- Step 5: 发货计划 ----
    # 先合并库存数据和 FBA 库存（发货计划需要知道总库存来判断运输方式）
    # SKU_Stock.csv 有: SKU, 国内库存, 在途库存, FBA库存
    df_inv_with_safety = df_inventory.merge(             # merge = INNER JOIN
        inventory_plan_df[["SKU", "安全库存"]],           # 只取 SKU + 安全库存两列
        on="SKU"                                         # 按 SKU 关联
    )
    shipment_plan_df = run_shipment_plan(
        supply_plan_df,                                  # 采购计划（含采购量 + 到货日）
        df_inv_with_safety                               # 库存 + 安全库存
    )

    # ---- 打包返回 ----
    return {
        "monthly": monthly,                              # 月度销量汇总（可用于下游分析）
        "demand_result": demand_result,                  # 需求预测完整结果
        "inventory_plan": inventory_plan_df,             # 库存计划表
        "supply_plan": supply_plan_df,                   # 采购计划表
        "shipment_plan": shipment_plan_df,               # 发货计划表
        "df_inventory": df_inventory,                    # 原始库存数据（备用）
        "df_sales": df_sales,                            # 原始日销量数据（历史看板用）
    }
