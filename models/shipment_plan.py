"""
发货计划模块 — 亚马逊单仓

策略:
  - 默认海运 (60天)
  - 库存低于安全库存时自动触发空运 (14天)
  - 发货日 = 到货日 (采购到货后即安排)
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.schemas import ShipmentPlanResult, ProcurementPlanResult
import config


def determine_freight_mode(current_stock: int, safety_stock: int) -> tuple:
    """
    判断运输方式

    Args:
        current_stock: 当前库存
        safety_stock: 安全库存

    Returns:
        (运输方式, 运输天数)
    """
    if current_stock < safety_stock:
        return "空运", config.AIR_FREIGHT_DAYS
    return "海运", config.SEA_FREIGHT_DAYS


def run_shipment_plan(
    df_procurement: pd.DataFrame,
    df_inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    发货计划主函数

    Args:
        df_procurement: 供应计划输出 (含 SKU, 最终采购量, 预计到货日)
        df_inventory: 当前库存 (含 当前库存, 安全库存 from forecast)

    Returns:
        ShipmentPlanResult DataFrame
    """
    sp = ShipmentPlanResult()
    pp = ProcurementPlanResult()

    # 只处理需要补货的SKU
    need_ship = df_procurement[df_procurement[pp.NEED_REPLENISH] == "是"].copy()

    if need_ship.empty:
        return pd.DataFrame(columns=sp.columns)

    results = []
    for _, row in need_ship.iterrows():
        sku = row[pp.SKU]
        final_qty = row[pp.FINAL_QTY]
        expected_arrival = row[pp.EXPECTED_ARRIVAL]

        # 获取当前库存和安全库存
        inv_row = df_inventory[df_inventory["SKU"] == sku]
        if inv_row.empty:
            continue
        current_stock = inv_row.iloc[0]["当前库存"]
        safety_stock = inv_row.iloc[0].get("安全库存", 0)

        # 判断运输方式
        freight_mode, freight_days = determine_freight_mode(current_stock, safety_stock)

        # 发货日 = 预计到货日（采购到货后安排发货）
        arrival_date = datetime.strptime(expected_arrival, "%Y-%m-%d")
        dispatch_date = arrival_date
        est_listing = dispatch_date + timedelta(days=freight_days)

        results.append({
            sp.SKU: sku,
            sp.WAREHOUSE: "亚马逊主仓",
            sp.SHIP_QTY: final_qty,
            sp.FREIGHT_MODE: freight_mode,
            sp.DISPATCH_DATE: dispatch_date.strftime("%Y-%m-%d"),
            sp.EST_ARRIVAL: est_listing.strftime("%Y-%m-%d"),
            sp.FREIGHT_DAYS: freight_days,
        })

    return pd.DataFrame(results)[sp.columns]
