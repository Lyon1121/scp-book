"""
供应链计划模型 —— Streamlit Dashboard

这是整个项目的用户界面，基于 Streamlit 构建。
打开后看到四个 Tab 页面，从左到右依次是：
  需求预测 → 库存计划 → 供应计划 → 发货计划

操作方式：
  1. 左侧栏设置参数（预测方法、窗口/α值、当前日期）
  2. 点击「运行 Pipeline」按钮
  3. 右侧四个 Tab 展示计算结果

配色：黑白灰（用户要求"最原始的黑白灰做展示"）
"""
import streamlit as st                                    # Streamlit 框架（pip install streamlit）
import pandas as pd                                       # 数据分析（DataFrame 展示用）
from datetime import datetime                             # 日期处理

import config                                             # 全局配置（在侧栏显示参数说明）
from pipeline import run_pipeline                         # 一键运行四模块
from utils import viz                                     # 可视化函数（Plotly 图表）


# ============================================================
# 页面全局配置
# ============================================================
st.set_page_config(
    page_title="供应链计划模型",                           # 浏览器标签页标题
    layout="wide",                                        # 宽屏布局（充分利用横向空间）
    initial_sidebar_state="expanded",                     # 初始侧栏展开（让用户看到参数面板）
)

# ============================================================
# 自定义 CSS（黑白灰配色，最简样式）
# ============================================================
st.markdown("""
<style>
    .stApp { background: #fafafa; }                       /* 整体背景：极浅灰 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }      /* Tab 之间的间距 */
    .stTabs [data-baseweb="tab"] {
        color: #333; background: #eee;                    /* Tab 文字深灰，背景浅灰 */
        border-radius: 4px 4px 0 0;                       /* 圆角上边 */
        padding: 8px 16px;                                /* 内边距 */
    }
    .stTabs [aria-selected="true"] {                      /* 当前选中的 Tab */
        background: #fff;                                 /* 白色背景 */
        border-bottom: 2px solid #333;                    /* 底部深灰下划线 */
    }
    .metric-card {                                        /* 指标卡片的容器 */
        border: 1px solid #ddd;                           /* 浅灰边框 */
        padding: 12px;                                    /* 内边距 */
        border-radius: 4px;                               /* 圆角 */
        background: #fff;                                 /* 白色背景 */
        text-align: center;                               /* 居中对齐 */
    }
    .metric-value {                                       /* 指标数值 */
        font-size: 24px; font-weight: bold; color: #111;  /* 大号加粗深黑 */
    }
    .metric-label {                                       /* 指标名称 */
        font-size: 12px; color: #888;                     /* 小号灰色 */
    }
</style>
""", unsafe_allow_html=True)                              # unsafe_allow_html=True 允许直接注入 HTML/CSS

# ---- 顶部标题 ----
st.title("供应链计划模型")                                 # 页面大标题
st.caption("中小企业跨境电商 · 需求预测 → 库存计划 → 供应计划 → 发货计划")  # 副标题小字


# ============================================================
# 侧边栏：参数设置区域
# ============================================================
with st.sidebar:                                           # st.sidebar 中的所有内容出现在左侧
    st.header("参数设置")                                   # 侧栏标题

    # --- 预测方法选择（下拉菜单） ---
    forecast_method = st.selectbox(
        "统计预测方法",                                     # 标签
        options=["moving_average", "exponential_smoothing"], # 选项
        format_func=lambda x: "移动平均" if x == "moving_average" else "指数平滑",  # 显示中文名
    )

    # --- 根据选择的方法显示不同的参数滑块 ---
    if forecast_method == "moving_average":                 # 选了移动平均
        window = st.slider(                                # 滑块控件
            "移动平均窗口 (月)",                            # 标签
            1, 12, 3                                       # (最小值, 最大值, 默认值)
        )
        kwargs = {"window": window}                        # 打包参数（透传给 get_forecaster）
    else:                                                   # 选了指数平滑
        alpha = st.slider(
            "平滑系数 α",                                   # 标签
            0.1, 0.9, 0.3, 0.05                            # (最小值, 最大值, 默认值, 步长)
        )
        kwargs = {"alpha": alpha}                          # 打包参数

    # --- 当前日期选择器 ---
    current_date = st.date_input(
        "当前日期",                                         # 标签
        value=datetime(2026, 1, 1)                          # 默认值：2026年1月1日
    )

    # --- 参数说明（只读，展示全局配置） ---
    st.divider()                                            # 分割线
    st.caption(f"采购 Lead Time: {config.PROCUREMENT_LEAD_TIME}天")  # 显示采购提前期
    st.caption(f"ROD 日: 每月{config.ROD_DAYS}")            # 显示 ROD 日期
    st.caption(f"海运: {config.SEA_FREIGHT_DAYS}天 | 空运: {config.AIR_FREIGHT_DAYS}天")  # 运输天数

    # --- 运行按钮 ---
    run_btn = st.button(
        "运行 Pipeline",                                    # 按钮文字
        type="primary",                                     # 主按钮样式（醒目）
        use_container_width=True                            # 按钮撑满侧栏宽度
    )

    # --- 底部备注 ---
    st.divider()
    st.caption("CSV 列名: SKU / 日期 / 销量 / 渠道")        # 提醒 CSV 格式


# ============================================================
# 主区域：运行 & 展示结果
# ============================================================
if not run_btn:                                             # 如果用户还没点"运行 Pipeline"
    st.info("👈 左侧配置参数后点击「运行 Pipeline」")        # 显示提示信息
    st.stop()                                               # 停止渲染（后面的代码不执行）

# --- 用户点了按钮，开始跑 Pipeline ---
with st.spinner("运行中..."):                               # 显示 Loading 动画
    try:
        result = run_pipeline(                              # 调 pipeline.py 的入口函数
            forecast_method=forecast_method,                # 预测方法（字符串）
            current_date=datetime.combine(                  # datetime.date → datetime.datetime
                current_date, datetime.min.time()           # .combine(日期, 时间) = 2026-01-01 00:00:00
            ),
            **kwargs,                                       # 展开参数（window 或 alpha）
        )
    except Exception as e:                                  # 捕获所有异常
        st.error(f"运行失败: {e}")                           # 显示红色错误信息
        st.stop()                                           # 停止渲染


# ============================================================
# 四页 Tab Dashboard
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([                         # st.tabs 创建多个标签页
    " 需求预测", " 库存计划", " 供应计划", " 发货计划",       # 四个 Tab 的名字
])


# ============================================================
# Tab 1: 需求预测
# ============================================================
with tab1:                                                  # with tab1: 表示在这个 Tab 内渲染
    demand = result["demand_result"]                        # 从 Pipeline 结果中取需求预测部分

    # --- 顶部指标卡片（4 个并排） ---
    s = demand["summary"]                                   # 汇总指标字典
    cols = st.columns(4)                                    # 创建 4 列布局
    cols[0].markdown(f'''<div class="metric-card">
        <div class="metric-value">{s.get("历史达成率_平均(%)", "-")}%</div>
        <div class="metric-label">历史平均达成率</div>
    </div>''', unsafe_allow_html=True)                      # 卡片1：平均达成率
    cols[1].markdown(f'''<div class="metric-card">
        <div class="metric-value">{s.get("历史MAPE_人工vs实际(%)", "-")}%</div>
        <div class="metric-label">历史 MAPE</div>
    </div>''', unsafe_allow_html=True)                      # 卡片2：MAPE
    cols[2].markdown(f'''<div class="metric-card">
        <div class="metric-value">{s.get("未来偏差_统计vs人工_平均(%)", "-")}%</div>
        <div class="metric-label">未来平均偏差</div>
    </div>''', unsafe_allow_html=True)                      # 卡片3：未来偏差
    cols[3].markdown(f'''<div class="metric-card">
        <div class="metric-value">{s.get("预测方法", "-")}</div>
        <div class="metric-label">统计方法</div>
    </div>''', unsafe_allow_html=True)                      # 卡片4：预测方法名

    st.divider()                                            # 分割线

    # --- 图表区：左右两列并排 ---
    col_l, col_r = st.columns(2)                            # 创建两列
    with col_l:
        # 左列：历史销量 vs 人工预测（折线对比图）
        st.plotly_chart(
            viz.plot_historical_compare(demand["historical_compare"]),
            use_container_width=True                        # 撑满列宽
        )
    with col_r:
        # 右列：达成率趋势图
        st.plotly_chart(
            viz.plot_achievement_rate(demand["historical_compare"]),
            use_container_width=True
        )

    # 全宽：未来预测对比（柱状图）
    st.plotly_chart(
        viz.plot_future_compare(demand["future_compare"]),
        use_container_width=True
    )

    # --- 数据明细表（折叠区） ---
    with st.expander("历史对比明细"):                        # expander = 可折叠区域
        st.dataframe(demand["historical_compare"], use_container_width=True)  # 展示 DataFrame
    with st.expander("未来对比明细"):
        st.dataframe(demand["future_compare"], use_container_width=True)


# ============================================================
# Tab 2: 库存计划
# ============================================================
with tab2:
    inv = result["inventory_plan"]                          # 库存计划表

    # 指标卡片（3 个）
    cols = st.columns(3)
    cols[0].markdown(f'''<div class="metric-card">
        <div class="metric-value">{inv["目标库存"].sum():,}</div>  <!-- :, 是千分位格式 -->
        <div class="metric-label">总目标库存 (件)</div>
    </div>''', unsafe_allow_html=True)
    cols[1].markdown(f'''<div class="metric-card">
        <div class="metric-value">{inv["安全库存"].sum():,}</div>
        <div class="metric-label">总安全库存 (件)</div>
    </div>''', unsafe_allow_html=True)
    cols[2].markdown(f'''<div class="metric-card">
        <div class="metric-value">{len(inv)}</div>
        <div class="metric-label">SKU 数</div>
    </div>''', unsafe_allow_html=True)

    st.divider()

    # 库存结构堆叠柱状图
    st.plotly_chart(viz.plot_inventory_structure(inv), use_container_width=True)

    # 库存明细表
    st.dataframe(inv, use_container_width=True)


# ============================================================
# Tab 3: 供应计划
# ============================================================
with tab3:
    sup = result["supply_plan"]                             # 采购计划表

    # 只统计"需要补货"的 SKU 的采购总量
    total_order = sup[sup["是否需要补货"] == "是"]["最终采购量"].sum()

    cols = st.columns(3)
    cols[0].markdown(f'''<div class="metric-card">
        <div class="metric-value">{total_order:,}</div>
        <div class="metric-label">总采购量 (件)</div>
    </div>''', unsafe_allow_html=True)
    cols[1].markdown(f'''<div class="metric-card">
        <div class="metric-value">{len(sup[sup["是否需要补货"] == "是"])}</div>
        <div class="metric-label">需补货SKU</div>
    </div>''', unsafe_allow_html=True)
    cols[2].markdown(f'''<div class="metric-card">
        <div class="metric-value">{sup["再订货日期"].iloc[0] if not sup.empty else "-"}</div>
        <div class="metric-label">下次ROD</div>
    </div>''', unsafe_allow_html=True)

    st.divider()
    st.dataframe(sup, use_container_width=True)

    # 导出按钮：把采购计划表导出为 CSV 文件
    csv = sup.to_csv(index=False).encode("utf-8-sig")       # DataFrame → CSV 字符串 → 字节
    st.download_button(
        "导出采购计划 CSV",                                  # 按钮文字
        csv,                                                # 文件内容
        "procurement_plan.csv",                             # 下载文件名
        "text/csv"                                          # MIME 类型
    )


# ============================================================
# Tab 4: 发货计划
# ============================================================
with tab4:
    ship = result["shipment_plan"]                          # 发货计划表

    if ship.empty:                                          # 如果没有需要发货的 SKU
        st.info("无需发货")                                 # 显示蓝色提示
    else:
        # 统计海运和空运的 SKU 数量
        sea_count = len(ship[ship["运输方式"] == "海运"])    # 走海运的 SKU 数
        air_count = len(ship[ship["运输方式"] == "空运"])    # 走空运的 SKU 数

        cols = st.columns(3)
        cols[0].markdown(f'''<div class="metric-card">
            <div class="metric-value">{ship["发货量"].sum():,}</div>
            <div class="metric-label">总发货量 (件)</div>
        </div>''', unsafe_allow_html=True)
        cols[1].markdown(f'''<div class="metric-card">
            <div class="metric-value">{sea_count} / {air_count}</div>
            <div class="metric-label">海运/空运 SKU数</div>
        </div>''', unsafe_allow_html=True)
        cols[2].markdown(f'''<div class="metric-card">
            <div class="metric-value">{ship["运输天数"].min()}~{ship["运输天数"].max()}天</div>
            <div class="metric-label">运输天数</div>
        </div>''', unsafe_allow_html=True)

        st.divider()
        st.dataframe(ship, use_container_width=True)

        # 导出按钮
        csv = ship.to_csv(index=False).encode("utf-8-sig")
        st.download_button("导出发货计划 CSV", csv, "shipment_plan.csv", "text/csv")
