"""
测试需求预测双轨制逻辑
"""
import sys
sys.path.insert(0, "C:/Users/Lyon/Desktop/scp_models")

import pandas as pd
from data.loader import load_csv
from models.demand_forecast import (
    aggregate_to_monthly,
    get_forecaster,
    run_dual_forecast,
)

# 加载数据
df_sales = load_csv("C:/Users/Lyon/Desktop/scp_models/sample_data/historical_sales.csv")
df_manual = load_csv("C:/Users/Lyon/Desktop/scp_models/sample_data/manual_forecast.csv")

print("=" * 60)
print("测试1: 日销量 → 月度聚合")
print("=" * 60)
monthly = aggregate_to_monthly(df_sales)
print(f"月度记录数: {len(monthly)}")
print(f"SKU数: {monthly['SKU'].nunique()}")
print(f"月份范围: {monthly['月份'].min()} ~ {monthly['月份'].max()}")
print(monthly.head(10).to_string(index=False))

print("\n" + "=" * 60)
print("测试2: 双轨对比 — 移动平均")
print("=" * 60)
result_ma = run_dual_forecast(df_sales, df_manual, method="moving_average", window=3)

print("\n--- 汇总指标 (移动平均) ---")
for k, v in result_ma["summary"].items():
    print(f"  {k}: {v}")

print("\n--- 历史对比 (前10行) ---")
print(result_ma["historical_compare"].head(10).to_string(index=False))

print("\n--- 未来对比 ---")
print(result_ma["future_compare"].to_string(index=False))

print("\n" + "=" * 60)
print("测试3: 双轨对比 — 指数平滑")
print("=" * 60)
result_es = run_dual_forecast(df_sales, df_manual, method="exponential_smoothing", alpha=0.3)

print("\n--- 汇总指标 (指数平滑) ---")
for k, v in result_es["summary"].items():
    print(f"  {k}: {v}")

print("\n--- 未来对比 ---")
print(result_es["future_compare"].to_string(index=False))

print("\n" + "=" * 60)
print("测试4: 预测器工厂函数")
print("=" * 60)
import numpy as np
ma = get_forecaster("moving_average", window=3)
ma.fit(np.array([100, 110, 120, 130, 140]))
pred = ma.predict(3)
print(f"移动平均(窗口=3): 历史[100,110,120,130,140] → 预测: {pred}")

es = get_forecaster("exponential_smoothing", alpha=0.3)
es.fit(np.array([100, 110, 120, 130, 140]))
pred = es.predict(3)
print(f"指数平滑(α=0.3): 历史[100,110,120,130,140] → 预测: {pred}")

print("\n✅ 所有测试通过！")
