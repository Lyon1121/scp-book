"""
可视化封装 —— Streamlit 页面上显示的图表

技术选型：
  使用 Plotly（而不是 Matplotlib），因为：
  1. 交互式（鼠标悬停显示数值、缩放、平移）
  2. 原生支持 Streamlit（st.plotly_chart 一行搞定）
  3. 不需要保存图片文件

配色规范：
  黑白灰三色调（用户要求"最原始的黑白灰做展示"）
    actual（实际）: #333333 深灰
    manual（人工）: #888888 中灰
    stat（统计）:   #000000 黑色
    label（标签）:  #666666 浅深灰
"""
import plotly.graph_objects as go                         # Plotly 图形对象（go.Scatter、go.Bar 等）
from plotly.subplots import make_subplots                 # 子图布局（当前未使用，预留）
import pandas as pd                                       # DataFrame 处理


# ============================================================
# 全局配色常量（黑白灰）
# ============================================================
COLORS = {
    "actual": "#333333",    # 实际销量 — 深灰实线（主角，最醒目）
    "manual": "#888888",    # 人工预测 — 中灰虚线（辅助线）
    "stat": "#000000",      # 统计预测 — 黑色柱子（对比人工的基准）
    "label": "#666666",     # 文字标签 — 中灰
}


# ============================================================
# 图1: 历史销量 vs 人工预测（双线对比）
# ============================================================
def plot_historical_compare(df: pd.DataFrame) -> go.Figure:
    """
    折线图：每个 SKU 两条线
      - 实线 = 实际销量
      - 虚线 = 人工预测

    目的：
      视觉上比较"销售人员的预测"和"真实发生的事"，差距一目了然。

    Args:
        df: 历史对比 DataFrame（来自 demand_forecast.compare_historical()）
            必须含: SKU, 月份, 实际销量, 人工预测量

    Returns:
        plotly Figure 对象（Streamlit 可直接渲染）
    """
    fig = go.Figure()                                    # 创建空白图形对象

    skus = df["SKU"].unique()                            # 获取所有 SKU（去重）
    for sku in skus:                                     # 每个 SKU 画两条线
        sku_df = df[df["SKU"] == sku].sort_values("月份") # 过滤出该 SKU，按月份排序

        # 线1: 实际销量（深灰实线）
        fig.add_trace(go.Scatter(                         # Scatter = 散点/折线图
            x=sku_df["月份"],                             # X 轴：月份
            y=sku_df["实际销量"],                          # Y 轴：实际销量
            mode="lines+markers",                         # 折线 + 数据点标记
            name=f"{sku} 实际",                           # 图例标签
            line=dict(color=COLORS["actual"], width=2),  # 深灰，线宽 2
        ))

        # 线2: 人工预测（中灰虚线）
        fig.add_trace(go.Scatter(
            x=sku_df["月份"],
            y=sku_df["人工预测量"],
            mode="lines+markers",
            name=f"{sku} 人工预测",
            line=dict(color=COLORS["manual"], width=1.5, dash="dash"),  # dash="dash" = 虚线
        ))

    # 全局布局设置
    fig.update_layout(
        title="历史销量 vs 人工预测",                     # 图表标题
        xaxis_title="月份",                               # X 轴标签
        yaxis_title="销量",                               # Y 轴标签
        template="plotly_white",                          # 白色主题（黑字白底）
        font=dict(color="#333"),                          # 全局字体颜色
    )
    return fig                                           # 返回图形（Streamlit 调用方用 st.plotly_chart() 渲染）


# ============================================================
# 图2: 人工预测达成率趋势
# ============================================================
def plot_achievement_rate(df: pd.DataFrame) -> go.Figure:
    """
    折线图：各 SKU 的人工预测达成率随时间变化

    参考线：
      100% 水平虚线 — 完美预测的基准

    解读：
      线在 100% 以上 → 销售超预期（预测偏保守）
      线在 100% 以下 → 未达预期（预测偏乐观）

    Args:
        df: 历史对比 DataFrame（含 达成率_人工 列）

    Returns:
        plotly Figure 对象
    """
    fig = go.Figure()

    skus = df["SKU"].unique()                            # 所有 SKU
    for sku in skus:
        sku_df = df[df["SKU"] == sku].sort_values("月份")
        fig.add_trace(go.Scatter(
            x=sku_df["月份"],
            y=sku_df["达成率_人工"],                      # Y 轴：达成率百分比
            mode="lines+markers",
            name=sku,
            line=dict(width=1.5),                        # 默认 Plotly 自动配色
        ))

    # 添加 100% 基准线
    fig.add_hline(                                       # add_hline = 添加水平参考线
        y=100,                                           # Y=100 的位置
        line_dash="dash",                                # 虚线
        line_color="#999",                               # 灰色
        annotation_text="100%",                          # 线上标注
    )

    fig.update_layout(
        title="人工预测达成率趋势",
        xaxis_title="月份",
        yaxis_title="达成率 (%)",
        template="plotly_white",
        font=dict(color="#333"),
    )
    return fig


# ============================================================
# 图3: 未来预测对比（人工 vs 统计）
# ============================================================
def plot_future_compare(df: pd.DataFrame) -> go.Figure:
    """
    分组柱状图：未来每个月的预测值对比

    每组两根柱子：
      - 灰柱 = 人工预测（销售直觉）
      - 黑柱 = 统计预测（数学模型）

    目的：
      直观比较两种预测体系的差异。
      柱子差不多高 → 两者一致（可信度高）
      柱子差很多 → 需要人工判断谁更合理

    Args:
        df: 未来对比 DataFrame（含 人工预测量, 统计预测量）

    Returns:
        plotly Figure 对象
    """
    fig = go.Figure()

    skus = df["SKU"].unique()
    for sku in skus:
        sku_df = df[df["SKU"] == sku].sort_values("月份")

        # 灰柱：人工预测
        fig.add_trace(go.Bar(                              # Bar = 柱状图
            x=sku_df["月份"],
            y=sku_df["人工预测量"],
            name=f"{sku} 人工",
            marker_color=COLORS["manual"],                 # 中灰
        ))

        # 黑柱：统计预测
        fig.add_trace(go.Bar(
            x=sku_df["月份"],
            y=sku_df["统计预测量"],
            name=f"{sku} 统计",
            marker_color=COLORS["stat"],                   # 黑色
        ))

    fig.update_layout(
        title="未来预测对比：人工 vs 统计",
        xaxis_title="月份",
        yaxis_title="预测量",
        template="plotly_white",
        font=dict(color="#333"),
        barmode="group",                                   # "group" = 分组柱状图（并排而非堆叠）
    )
    return fig


# ============================================================
# 图4: 库存结构图（安全库存 vs 周转库存）
# ============================================================
def plot_inventory_structure(df: pd.DataFrame) -> go.Figure:
    """
    堆叠柱状图：每个 SKU 的库存 = 安全库存（下层）+ 周转库存（上层）

    目的：
      一眼看出每个 SKU 的总目标库存以及两种库存的占比。
      安全库存占比大 → 该 SKU 波动大，需要更多缓冲
      周转库存占比大 → 该 SKU 稳定，库存主要满足日常消耗

    Args:
        df: 库存计划 DataFrame（含 SKU, 安全库存, 周转库存）

    Returns:
        plotly Figure 对象
    """
    fig = go.Figure()

    # 下层（灰）：周转库存
    fig.add_trace(go.Bar(
        x=df["SKU"],
        y=df["周转库存"],
        name="周转库存",
        marker_color="#999",                              # 浅灰
    ))

    # 上层（黑）：安全库存
    fig.add_trace(go.Bar(
        x=df["SKU"],
        y=df["安全库存"],
        name="安全库存",
        marker_color="#333",                              # 深灰
    ))

    fig.update_layout(
        title="库存结构",
        xaxis_title="SKU",
        yaxis_title="库存量",
        template="plotly_white",
        font=dict(color="#333"),
        barmode="stack",                                   # "stack" = 堆叠柱状图
    )
    return fig
