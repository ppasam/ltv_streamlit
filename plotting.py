"""Plotting module for LTV analysis visualizations."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_profit_by_channel_pie_chart(profit_by_channel_df: pd.DataFrame) -> go.Figure:
    """Create pie chart for profit by channel."""
    if profit_by_channel_df.empty:
        return None
    
    profit_by_channel_df = profit_by_channel_df.copy()
    
    if "Канал" in profit_by_channel_df.columns:
        profit_by_channel_df = profit_by_channel_df.set_index("Канал")
    
    if "ИТОГО" in profit_by_channel_df.index:
        profit_by_channel_df = profit_by_channel_df.drop("ИТОГО")
    
    if "Сумма" not in profit_by_channel_df.columns:
        return None
    
    fig = px.pie(
        profit_by_channel_df,
        values="Сумма",
        names=profit_by_channel_df.index,
        title="Прибыль по каналам привлечения",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(
        textinfo="percent+label",
        pull=[0.05] * len(profit_by_channel_df),
        textposition="outside"
    )
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        title_font=dict(size=18, color="#2C3E50"),
        margin=dict(t=80, b=80, l=40, r=40)
    )
    
    return fig


def create_orders_by_channel_pie_chart(orders_by_channel_df: pd.DataFrame) -> go.Figure:
    """Create pie chart for orders by channel."""
    if orders_by_channel_df.empty:
        return None
    
    orders_by_channel_df = orders_by_channel_df.copy()
    
    if "Канал" in orders_by_channel_df.columns:
        orders_by_channel_df = orders_by_channel_df.set_index("Канал")
    
    if "ИТОГО" in orders_by_channel_df.index:
        orders_by_channel_df = orders_by_channel_df.drop("ИТОГО")
    
    if "Сумма" not in orders_by_channel_df.columns:
        return None
    
    fig = px.pie(
        orders_by_channel_df,
        values="Сумма",
        names=orders_by_channel_df.index,
        title="Количество заказов по каналам привлечения",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig.update_traces(
        textinfo="percent+label",
        pull=[0.05] * len(orders_by_channel_df),
        textposition="outside"
    )
    
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        title_font=dict(size=18, color="#2C3E50"),
        margin=dict(t=80, b=80, l=40, r=40)
    )
    
    return fig