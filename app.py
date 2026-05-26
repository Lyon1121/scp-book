"""
供应链计划模型 — Streamlit Dashboard (黑白灰)
"""
import streamlit as st
import pandas as pd
from datetime import datetime

import config
from pipeline import run_pipeline
from utils import viz

# ---- 页面配置 ----
st.set_page_config(
    page_title="供应链计划模型",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 黑白灰样式（最简）
st.markdown("""
<style>
    .stApp { background: #fafafa; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        color: #333; background: #eee; border-radius: 4px 4px 0 0;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] { background: #fff; border-bottom: 2px solid #333; }
    .metric-card {
        border: 1px solid #ddd; padding: 12px; border-radius: 4px;
        background: #fff; text-align: center;
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #111; }
    .metric-label { font-size: 12px; color: #888; }
</style>
""", unsafe_allow_html=True)

st.title("供应链计划模型")
st.caption("中小企业跨境电商 · 需求预测 → 库存计划 → 供应计划 → 发货计划")

# ---- 侧边栏: 参数 ----
with st.sidebar:
    st.header("参数设置")

    forecast_method = st.selectbox(
        "统计预测方法",
        options=["moving_average", "exponential_smoothing"],
        format_func=lambda x: "移动平均" if x == "moving_average" else "指数平滑",
    )

    if forecast_method == "moving_average":
        window = st.slider("移动平均窗口 (月)", 1, 12, 3)
        kwargs = {"window": window}
    else:
        alpha = st.slider("平滑系数 α", 0.1, 0.9, 0.3, 0.05)
        kwargs = {"alpha": alpha}

    current_date = st.date_input("当前日期", value=datetime(2026, 1, 1))

    st.divider()
    st.caption(f"采购 Lead Time: {config.PROCUREMENT_LEAD_TIME}天")
    st.caption(f"ROD 日: 每月{config.ROD_DAYS}")
    st.caption(f"海运: {config.SEA_FREIGHT_DAYS}天 | 空运: {config.AIR_FREIGHT_DAYS}天")

    run_btn = st.button("运行 Pipeline", type="primary", use_container_width=True)

    st.divider()
    st.caption("CSV 列名: SKU / 日期 / 销量 / 渠道")

# ---- 主区域 ----
if not run_btn:
    st.info("👈 左侧配置参数后点击「运行 Pipeline」")
    st.stop()

# 运行 Pipeline
with st.spinner("运行中..."):
    try:
        result = run_pipeline(
            forecast_method=forecast_method,
            current_date=datetime.combine(current_date, datetime.min.time()),
            **kwargs,
        )
    except Exception as e:
        st.error(f"运行失败: {e}")
        st.stop()

# ---- 四页 Dashboard ----
tab1, tab2, tab3, tab4 = st.tabs([
    " 需求预测", " 库存计划", " 供应计划", " 发货计划",
])

# ============================================================
# 页1: 需求预测
# ============================================================
with tab1:
    demand = result["demand_result"]

    # 指标卡片
    s = demand["summary"]
    cols = st.columns(4)
    cols[0].markdown(f'<div class="metric-card"><div class="metric-value">{s.get("历史达成率_平均(%)", "-")}%</div><div class="metric-label">历史平均达成率</div></div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="metric-card"><div class="metric-value">{s.get("历史MAPE_人工vs实际(%)", "-")}%</div><div class="metric-label">历史 MAPE</div></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="metric-card"><div class="metric-value">{s.get("未来偏差_统计vs人工_平均(%)", "-")}%</div><div class="metric-label">未来平均偏差</div></div>', unsafe_allow_html=True)
    cols[3].markdown(f'<div class="metric-card"><div class="metric-value">{s.get("预测方法", "-")}</div><div class="metric-label">统计方法</div></div>', unsafe_allow_html=True)

    st.divider()

    # 图表
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(viz.plot_historical_compare(demand["historical_compare"]), use_container_width=True)
    with col_r:
        st.plotly_chart(viz.plot_achievement_rate(demand["historical_compare"]), use_container_width=True)

    st.plotly_chart(viz.plot_future_compare(demand["future_compare"]), use_container_width=True)

    # 数据表
    with st.expander("历史对比明细"):
        st.dataframe(demand["historical_compare"], use_container_width=True)
    with st.expander("未来对比明细"):
        st.dataframe(demand["future_compare"], use_container_width=True)

# ============================================================
# 页2: 库存计划
# ============================================================
with tab2:
    inv = result["inventory_plan"]

    cols = st.columns(3)
    cols[0].markdown(f'<div class="metric-card"><div class="metric-value">{inv["目标库存"].sum():,}</div><div class="metric-label">总目标库存 (件)</div></div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="metric-card"><div class="metric-value">{inv["安全库存"].sum():,}</div><div class="metric-label">总安全库存 (件)</div></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="metric-card"><div class="metric-value">{len(inv)}</div><div class="metric-label">SKU 数</div></div>', unsafe_allow_html=True)

    st.divider()
    st.plotly_chart(viz.plot_inventory_structure(inv), use_container_width=True)

    st.dataframe(inv, use_container_width=True)

# ============================================================
# 页3: 供应计划
# ============================================================
with tab3:
    sup = result["supply_plan"]

    total_order = sup[sup["是否需要补货"] == "是"]["最终采购量"].sum()
    cols = st.columns(3)
    cols[0].markdown(f'<div class="metric-card"><div class="metric-value">{total_order:,}</div><div class="metric-label">总采购量 (件)</div></div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="metric-card"><div class="metric-value">{len(sup[sup["是否需要补货"] == "是"])}</div><div class="metric-label">需补货SKU</div></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="metric-card"><div class="metric-value">{sup["再订货日期"].iloc[0] if not sup.empty else "-"}</div><div class="metric-label">下次ROD</div></div>', unsafe_allow_html=True)

    st.divider()
    st.dataframe(sup, use_container_width=True)

    # 导出
    csv = sup.to_csv(index=False).encode("utf-8-sig")
    st.download_button("导出采购计划 CSV", csv, "procurement_plan.csv", "text/csv")

# ============================================================
# 页4: 发货计划
# ============================================================
with tab4:
    ship = result["shipment_plan"]

    if ship.empty:
        st.info("无需发货")
    else:
        sea_count = len(ship[ship["运输方式"] == "海运"])
        air_count = len(ship[ship["运输方式"] == "空运"])

        cols = st.columns(3)
        cols[0].markdown(f'<div class="metric-card"><div class="metric-value">{ship["发货量"].sum():,}</div><div class="metric-label">总发货量 (件)</div></div>', unsafe_allow_html=True)
        cols[1].markdown(f'<div class="metric-card"><div class="metric-value">{sea_count} / {air_count}</div><div class="metric-label">海运/空运 SKU数</div></div>', unsafe_allow_html=True)
        cols[2].markdown(f'<div class="metric-card"><div class="metric-value">{ship["运输天数"].min()}~{ship["运输天数"].max()}天</div><div class="metric-label">运输天数</div></div>', unsafe_allow_html=True)

        st.divider()
        st.dataframe(ship, use_container_width=True)

        csv = ship.to_csv(index=False).encode("utf-8-sig")
        st.download_button("导出发货计划 CSV", csv, "shipment_plan.csv", "text/csv")
