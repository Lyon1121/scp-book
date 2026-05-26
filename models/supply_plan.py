"""
供应计划模块 — ROD（再订货日期）策略

策略: 每月1号 & 15号为集中采购日
  采购量 = 目标库存 - 当前库存 - 在途库存 + 覆盖至下次到货的需求
  Lead Time = 30天
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.schemas import ProcurementPlanResult, InventoryPlanResult
import config


def get_upcoming_rod_dates(current_date: datetime, months_ahead: int = 3) -> list:
    """
    获取未来 N 个月的 ROD 日期

    Args:
        current_date: 当前日期
        months_ahead: 向前看几个月

    Returns:
        [(rod_date, expected_arrival_date), ...]
    """
    dates = []
    year = current_date.year
    month = current_date.month

    for _ in range(months_ahead + 2):  # 多算2个月保证覆盖
        for day in config.ROD_DAYS:
            rod = datetime(year, month, day)
            if rod >= current_date:
                arrival = rod + timedelta(days=config.PROCUREMENT_LEAD_TIME)
                dates.append((rod, arrival))
        month += 1
        if month > 12:
            month = 1
            year += 1

    return dates[:months_ahead * 2]  # 每月2次 × N月


def calculate_procurement(
    inventory_row: pd.Series,
    forecast_row: pd.Series,
    next_rod: datetime,
    next_arrival: datetime,
    days_to_next_rod: int,
) -> dict:
    """
    计算单个SKU在某ROD日期的采购量

    Args:
        inventory_row: 当前库存行 (SKU, 当前库存, 在途库存)
        forecast_row: 预测行 (日均需求)
        next_rod: 下一个ROD日期
        next_arrival: 预计到货日期
        days_to_next_rod: 距离下次补货窗口的天数

    Returns:
        dict with procurement result
    """
    current_stock = inventory_row["当前库存"]
    in_transit = inventory_row["在途库存"]
    daily_demand = forecast_row["日均需求"]
    safety_stock = forecast_row["安全库存"]
    target_inventory = forecast_row["目标库存"]

    # 到货前的总需求 = 日均需求 × (Lead Time + 到货后覆盖到下次ROD的天数)
    # 简单估算: 覆盖到下次补货到货的天数
    demand_until_next = daily_demand * config.PROCUREMENT_LEAD_TIME

    # 到货时的预计库存 = 当前库存 + 在途 - 期间需求
    projected_stock = current_stock + in_transit - demand_until_next

    # 建议采购量 = 目标库存 - 预计库存
    suggested_qty = target_inventory - projected_stock

    # 最小起订量约束
    moq = inventory_row.get("最小起订量", config.DEFAULT_MOQ)
    if suggested_qty > 0 and suggested_qty < moq:
        final_qty = moq
    elif suggested_qty > 0:
        final_qty = int(np.ceil(suggested_qty))
    else:
        final_qty = 0

    need_replenish = final_qty > 0

    return {
        "SKU": inventory_row["SKU"],
        "再订货日期": next_rod.strftime("%Y-%m-%d"),
        "当前库存": current_stock,
        "在途库存": in_transit,
        "安全库存": safety_stock,
        "目标库存": target_inventory,
        "建议采购量": max(0, int(np.ceil(suggested_qty))),
        "最终采购量": final_qty,
        "预计到货日": next_arrival.strftime("%Y-%m-%d"),
        "是否需要补货": "是" if need_replenish else "否",
    }


def run_supply_plan(
    df_inventory: pd.DataFrame,
    df_forecast: pd.DataFrame,
    current_date: datetime = None,
    months_ahead: int = 3,
) -> pd.DataFrame:
    """
    供应计划主函数（ROD策略）

    Args:
        df_inventory: 当前库存 DataFrame (SKU, 当前库存, 在途库存)
        df_forecast: 库存计划输出 (含 日均需求, 安全库存, 目标库存)
        current_date: 当前日期 (默认今天)
        months_ahead: 规划未来几个月的采购

    Returns:
        ProcurementPlanResult DataFrame
    """
    if current_date is None:
        current_date = datetime.now()

    pp = ProcurementPlanResult()

    # 获取未来ROD日期
    rod_dates = get_upcoming_rod_dates(current_date, months_ahead)

    # 合并库存和预测数据
    merged = df_inventory.merge(df_forecast, on="SKU", how="inner")

    results = []
    for sku in merged["SKU"].unique():
        sku_data = merged[merged["SKU"] == sku].iloc[0]

        for next_rod, next_arrival in rod_dates[:1]:  # 只看最近一次ROD
            result = calculate_procurement(
                sku_data, sku_data, next_rod, next_arrival, 0
            )
            results.append(result)

    return pd.DataFrame(results)[pp.columns[:len(results[0])]]
