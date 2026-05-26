"""
端到端 Pipeline — 串联四个模块
"""
import pandas as pd
from datetime import datetime
from pathlib import Path

import config
from data.loader import load_csv
from models.demand_forecast import run_dual_forecast, aggregate_to_monthly
from models.inventory_plan import run_inventory_plan
from models.supply_plan import run_supply_plan
from models.shipment_plan import run_shipment_plan


def run_pipeline(
    sales_path: str = None,
    manual_forecast_path: str = None,
    inventory_path: str = None,
    forecast_method: str = "moving_average",
    current_date: datetime = None,
    **forecast_kwargs,
) -> dict:
    """
    一键运行完整供应链计划 Pipeline

    Returns:
        dict:
          - monthly: 月度销售数据
          - demand_result: 需求预测结果 {historical_compare, future_compare, summary}
          - inventory_plan: 库存计划 DataFrame
          - supply_plan: 供应计划 DataFrame
          - shipment_plan: 发货计划 DataFrame
          - df_inventory: 当前库存原始数据
    """
    data_dir = config.DATA_DIR if sales_path is None else Path(sales_path).parent
    if sales_path is None:
        sales_path = data_dir / "historical_sales.csv"
    if manual_forecast_path is None:
        manual_forecast_path = data_dir / "manual_forecast.csv"
    if inventory_path is None:
        inventory_path = data_dir / "current_inventory.csv"
    if current_date is None:
        current_date = datetime.now()

    # 1. 加载数据
    df_sales = load_csv(str(sales_path))
    df_manual = load_csv(str(manual_forecast_path))
    df_inventory = load_csv(str(inventory_path))

    # 2. 需求预测（双轨）
    demand_result = run_dual_forecast(df_sales, df_manual, method=forecast_method, **forecast_kwargs)

    # 3. 库存计划
    monthly = aggregate_to_monthly(df_sales)
    inventory_plan_df = run_inventory_plan(monthly)

    # 4. 供应计划
    supply_plan_df = run_supply_plan(df_inventory, inventory_plan_df, current_date=current_date)

    # 5. 发货计划
    shipment_plan_df = run_shipment_plan(
        supply_plan_df,
        df_inventory.merge(inventory_plan_df[["SKU", "安全库存"]], on="SKU")
    )

    return {
        "monthly": monthly,
        "demand_result": demand_result,
        "inventory_plan": inventory_plan_df,
        "supply_plan": supply_plan_df,
        "shipment_plan": shipment_plan_df,
        "df_inventory": df_inventory,
    }
