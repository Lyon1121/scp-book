"""
可视化封装 — 黑白灰配色
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# 黑白灰色调
COLORS = {
    "actual": "#333333",
    "manual": "#888888",
    "stat": "#000000",
    "label": "#666666",
}


def plot_historical_compare(df: pd.DataFrame) -> go.Figure:
    """历史对比图：实际 vs 人工预测"""
    fig = go.Figure()

    skus = df["SKU"].unique()
    for sku in skus:
        sku_df = df[df["SKU"] == sku].sort_values("月份")
        fig.add_trace(go.Scatter(
            x=sku_df["月份"], y=sku_df["实际销量"],
            mode="lines+markers", name=f"{sku} 实际",
            line=dict(color=COLORS["actual"], width=2),
        ))
        fig.add_trace(go.Scatter(
            x=sku_df["月份"], y=sku_df["人工预测量"],
            mode="lines+markers", name=f"{sku} 人工预测",
            line=dict(color=COLORS["manual"], width=1.5, dash="dash"),
        ))

    fig.update_layout(
        title="历史销量 vs 人工预测",
        xaxis_title="月份",
        yaxis_title="销量",
        template="plotly_white",
        font=dict(color="#333"),
    )
    return fig


def plot_achievement_rate(df: pd.DataFrame) -> go.Figure:
    """达成率趋势图"""
    fig = go.Figure()

    skus = df["SKU"].unique()
    for sku in skus:
        sku_df = df[df["SKU"] == sku].sort_values("月份")
        fig.add_trace(go.Scatter(
            x=sku_df["月份"], y=sku_df["达成率_人工"],
            mode="lines+markers", name=sku,
            line=dict(width=1.5),
        ))

    fig.add_hline(y=100, line_dash="dash", line_color="#999",
                  annotation_text="100%")

    fig.update_layout(
        title="人工预测达成率趋势",
        xaxis_title="月份",
        yaxis_title="达成率 (%)",
        template="plotly_white",
        font=dict(color="#333"),
    )
    return fig


def plot_future_compare(df: pd.DataFrame) -> go.Figure:
    """未来对比图：人工预测 vs 统计预测"""
    fig = go.Figure()

    skus = df["SKU"].unique()
    for sku in skus:
        sku_df = df[df["SKU"] == sku].sort_values("月份")
        fig.add_trace(go.Bar(
            x=sku_df["月份"], y=sku_df["人工预测量"],
            name=f"{sku} 人工", marker_color=COLORS["manual"],
        ))
        fig.add_trace(go.Bar(
            x=sku_df["月份"], y=sku_df["统计预测量"],
            name=f"{sku} 统计", marker_color=COLORS["stat"],
        ))

    fig.update_layout(
        title="未来预测对比：人工 vs 统计",
        xaxis_title="月份",
        yaxis_title="预测量",
        template="plotly_white",
        font=dict(color="#333"),
        barmode="group",
    )
    return fig


def plot_inventory_structure(df: pd.DataFrame) -> go.Figure:
    """库存结构图（安全库存 vs 周转库存）"""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["SKU"], y=df["周转库存"],
        name="周转库存", marker_color="#999",
    ))
    fig.add_trace(go.Bar(
        x=df["SKU"], y=df["安全库存"],
        name="安全库存", marker_color="#333",
    ))

    fig.update_layout(
        title="库存结构",
        xaxis_title="SKU",
        yaxis_title="库存量",
        template="plotly_white",
        font=dict(color="#333"),
        barmode="stack",
    )
    return fig
