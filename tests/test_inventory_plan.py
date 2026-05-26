"""
测试库存计划模块
"""
import sys
sys.path.insert(0, "C:/Users/Lyon/Desktop/scp_models")

from data.loader import load_csv
from models.demand_forecast import aggregate_to_monthly
from models.inventory_plan import run_inventory_plan

df_sales = load_csv("C:/Users/Lyon/Desktop/scp_models/sample_data/historical_sales.csv")
monthly = aggregate_to_monthly(df_sales)

result = run_inventory_plan(monthly)

print("=" * 60)
print("库存计划结果")
print("=" * 60)
print(result.to_string(index=False))

print(f"\n汇总:")
print(f"  总目标库存: {result['目标库存'].sum():,} 件")
for sku in result["SKU"]:
    row = result[result["SKU"] == sku].iloc[0]
    print(f"  {sku}: {row['ABC分类']}{row['XYZ分类']}类, "
          f"安全库存={row['安全库存']}, 周转库存={row['周转库存']}, "
          f"目标库存={row['目标库存']}")

print("\n✅ 库存计划测试通过！")
