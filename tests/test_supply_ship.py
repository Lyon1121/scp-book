"""
测试供应计划 + 发货计划联动
"""
import sys
sys.path.insert(0, "C:/Users/Lyon/Desktop/scp_models")

import pandas as pd
from datetime import datetime
from data.loader import load_csv
from models.demand_forecast import aggregate_to_monthly
from models.inventory_plan import run_inventory_plan
from models.supply_plan import run_supply_plan
from models.shipment_plan import run_shipment_plan

# 加载数据
df_sales = load_csv("C:/Users/Lyon/Desktop/scp_models/sample_data/historical_sales.csv")
df_inv = load_csv("C:/Users/Lyon/Desktop/scp_models/sample_data/current_inventory.csv")

# 1. 月度聚合 → 2. 库存计划
monthly = aggregate_to_monthly(df_sales)
df_forecast = run_inventory_plan(monthly)

print("=" * 60)
print("供应计划 (ROD策略)")
print("=" * 60)
df_supply = run_supply_plan(df_inv, df_forecast, current_date=datetime(2026, 1, 1))
print(df_supply.to_string(index=False))

print("\n" + "=" * 60)
print("发货计划")
print("=" * 60)
df_ship = run_shipment_plan(df_supply, df_inv.merge(df_forecast[["SKU", "安全库存"]], on="SKU"))
print(df_ship.to_string(index=False))

# 验证
print("\n--- 验证 ---")
for _, row in df_supply.iterrows():
    print(f"  {row['SKU']}: 采购{row['最终采购量']}件, 到货{row['预计到货日']}")
for _, row in df_ship.iterrows():
    print(f"  {row['SKU']}: {row['运输方式']}({row['运输天数']}天), "
          f"发货{row['发货量']}件 → 上架{row['预计上架日']}")

print("\n✅ 供应+发货联动测试通过！")
