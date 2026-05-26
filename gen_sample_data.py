"""
生成模拟数据脚本
- historical_sales.csv: 24个月 × 3 SKU 日销量（含渠道）
- manual_forecast.csv: 24个月历史 + 6个月未来 月度人工预测
- current_inventory.csv / product_master.csv 更新
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

OUT_DIR = Path("C:/Users/Lyon/Desktop/scp_models/sample_data")
np.random.seed(42)

# ============================================================
# 1. historical_sales.csv — 24个月日销量
# ============================================================
print("生成 historical_sales.csv ...")

sku_config = {
    "SKU001": {"base": 150, "trend": 0.5, "season_amp": 30, "price": 45.0},
    "SKU002": {"base": 100, "trend": 0.3, "season_amp": 15, "price": 32.0},
    "SKU003": {"base": 220, "trend": 0.8, "season_amp": 50, "price": 78.0},
}

channels = ["亚马逊", "独立站"]
channel_ratio = {"亚马逊": 0.7, "独立站": 0.3}

start_date = datetime(2024, 1, 1)
end_date = datetime(2025, 12, 31)

rows = []
current = start_date
while current <= end_date:
    day_of_year = current.timetuple().tm_yday
    month_num = current.month
    # 季节性因子（年底旺季）
    season = 1.0 + 0.3 * np.sin(2 * np.pi * (month_num - 1) / 12)

    for sku, cfg in sku_config.items():
        # 基准量 + 线性趋势 + 季节性 + 随机波动
        base = cfg["base"] + cfg["trend"] * (month_num + (current.year - 2024) * 12)
        demand = base * season + np.random.normal(0, base * 0.08)
        demand = max(0, int(demand))

        for ch in channels:
            ch_demand = int(demand * channel_ratio[ch] * np.random.uniform(0.85, 1.15))
            ch_demand = max(0, ch_demand)
            rows.append({
                "SKU": sku,
                "日期": current.strftime("%Y-%m-%d"),
                "销量": ch_demand,
                "渠道": ch,
            })

    current += timedelta(days=1)

df_sales = pd.DataFrame(rows)
df_sales.to_csv(OUT_DIR / "historical_sales.csv", index=False, encoding="utf-8-sig")
print(f"  → {len(df_sales)} 行, {df_sales['SKU'].nunique()} SKU, {df_sales['渠道'].nunique()} 渠道")
print(f"  日期范围: {df_sales['日期'].min()} ~ {df_sales['日期'].max()}")

# ============================================================
# 2. manual_forecast.csv — 24个月历史 + 6个月未来人工预测
# ============================================================
print("\n生成 manual_forecast.csv ...")

# 先生成实际月度销量（用于制造"看起来合理"的人工预测）
df_sales["月份"] = df_sales["日期"].str[:7]
monthly_actual = df_sales.groupby(["SKU", "月份"])["销量"].sum().reset_index()

forecast_rows = []

# 24个月历史人工预测（基于实际值加偏置，模拟销售人员的乐观/保守）
for _, row in monthly_actual.iterrows():
    actual = row["销量"]
    # 人工预测：实际值 + 偏置（5%~15%误差），模拟销售人员预测不完美
    bias = np.random.choice([-0.1, -0.05, 0.0, 0.05, 0.10, 0.15])
    manual_fc = int(actual * (1 + bias) * np.random.uniform(0.90, 1.10))
    manual_fc = max(1, manual_fc)
    forecast_rows.append({
        "SKU": row["SKU"],
        "月份": row["月份"],
        "人工预测量": manual_fc,
        "类型": "历史",
    })

# 6个月未来人工预测（2026-01 ~ 2026-06）
# 基于最后6个月的趋势外推
for sku in sku_config:
    last_6 = monthly_actual[monthly_actual["SKU"] == sku].tail(6)["销量"].values
    last_6_avg = last_6.mean() if len(last_6) > 0 else sku_config[sku]["base"] * 30

    for m in range(1, 7):
        month_str = f"2026-{m:02d}"
        # 未来预测：最后6月均值 + 季节性 + 人工乐观偏置
        season = 1.0 + 0.3 * np.sin(2 * np.pi * (m - 1) / 12)
        manual_fc = int(last_6_avg * season * np.random.uniform(0.95, 1.15))
        manual_fc = max(1, manual_fc)
        forecast_rows.append({
            "SKU": sku,
            "月份": month_str,
            "人工预测量": manual_fc,
            "类型": "未来",
        })

df_forecast = pd.DataFrame(forecast_rows)
df_forecast.to_csv(OUT_DIR / "manual_forecast.csv", index=False, encoding="utf-8-sig")
print(f"  → {len(df_forecast)} 行")
print(f"  历史: {len(df_forecast[df_forecast['类型']=='历史'])} 行, "
      f"未来: {len(df_forecast[df_forecast['类型']=='未来'])} 行")

# ============================================================
# 3. current_inventory.csv
# ============================================================
print("\n生成 current_inventory.csv ...")
df_inv = pd.DataFrame([
    {"SKU": "SKU001", "当前库存": 1500, "在途库存": 500, "仓库": "亚马逊主仓"},
    {"SKU": "SKU002", "当前库存": 900,  "在途库存": 300, "仓库": "亚马逊主仓"},
    {"SKU": "SKU003", "当前库存": 2200, "在途库存": 800, "仓库": "亚马逊主仓"},
])
df_inv.to_csv(OUT_DIR / "current_inventory.csv", index=False, encoding="utf-8-sig")
print(f"  → {len(df_inv)} SKU")

# ============================================================
# 4. product_master.csv
# ============================================================
print("\n生成 product_master.csv ...")
df_prod = pd.DataFrame([
    {"SKU": "SKU001", "产品名称": "蓝牙耳机Pro",  "品类": "A类电子", "提前期_天": 30, "最小起订量": 100, "成本单价": 45.0},
    {"SKU": "SKU002", "产品名称": "USB充电线",    "品类": "B类配件", "提前期_天": 30, "最小起订量": 200, "成本单价": 32.0},
    {"SKU": "SKU003", "产品名称": "智能音箱",      "品类": "A类电子", "提前期_天": 30, "最小起订量": 50,  "成本单价": 78.0},
])
df_prod.to_csv(OUT_DIR / "product_master.csv", index=False, encoding="utf-8-sig")
print(f"  → {len(df_prod)} SKU")

print("\n✅ 全部数据生成完成！")
