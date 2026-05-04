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


def create_avg_profit_bar_chart(avg_profit_df: pd.DataFrame) -> go.Figure:
    """Create bar chart for average profit per order by channel."""
    if avg_profit_df.empty:
        return None
    
    avg_profit_df = avg_profit_df.copy()
    
    has_total = "ИТОГО" in avg_profit_df.index
    total_value = 0
    if has_total:
        total_value = avg_profit_df.loc["ИТОГО", "Сумма"] if "Сумма" in avg_profit_df.columns else 0
        avg_profit_df = avg_profit_df.drop("ИТОГО")
    
    if "Канал" in avg_profit_df.columns:
        avg_profit_df = avg_profit_df.set_index("Канал")
    
    if "Сумма" not in avg_profit_df.columns:
        return None
    
    fig = px.bar(
        avg_profit_df,
        y="Сумма",
        x=avg_profit_df.index,
        title="Средняя прибыль с заказа",
        color="Сумма",
        color_continuous_scale="Blues",
        text_auto=".2f"
    )
    
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=14, color="#1a1a1a")
    )
    
    if has_total and total_value > 0:
        fig.add_hline(
            y=total_value,
            line_dash="dash",
            line_color="red",
            line_width=3,
            annotation_text=f"ИТОГО: {total_value:.2f}",
            annotation_position="top right",
            annotation_font=dict(color="red", size=16, family="Arial Black")
        )
    
    fig.update_layout(
        xaxis_title=dict(text="Канал", font=dict(size=16, color="#1a1a1a", family="Arial")),
        yaxis_title=dict(text="Средняя прибыль с заказа", font=dict(size=16, color="#1a1a1a", family="Arial")),
        showlegend=False,
        title_font=dict(size=20, color="#1a1a1a", family="Arial Black"),
        margin=dict(t=100, b=80, l=80, r=40),
        plot_bgcolor="rgba(255,255,255,0.9)",
        paper_bgcolor="white",
        font=dict(size=14, color="#1a1a1a", family="Arial")
    )
    
    fig.update_xaxes(tickfont=dict(size=14, color="#1a1a1a"))
    fig.update_yaxes(tickfont=dict(size=14, color="#1a1a1a"))

    return fig


def create_profit_trend_chart(profit_df: pd.DataFrame) -> go.Figure:
    """Create line chart for profit trend by channel and cohort periods."""
    if profit_df.empty:
        return None

    profit_df = profit_df.copy()

    channels = list(profit_df.index)
    if "ИТОГО" in channels:
        channels.remove("ИТОГО")

    columns = [col for col in profit_df.columns if col != "ВСЕГО"]

    if not channels or not columns:
        return None

    fig = go.Figure()

    colors = px.colors.qualitative.Set2 + px.colors.qualitative.Dark24

    for i, channel in enumerate(channels):
        fig.add_trace(go.Scatter(
            x=columns,
            y=profit_df.loc[channel].values,
            mode="lines+markers+text" if len(columns) <= 10 else "lines+markers",
            name=channel,
            line=dict(width=3, color=colors[i % len(colors)]),
            marker=dict(size=10, symbol="circle"),
            text=[f"{v:,.2f}".replace(",", " ") for v in profit_df.loc[channel].values],
            textposition="top center",
            textfont=dict(size=10, color="#1a1a1a")
        ))

    fig.update_layout(
        title=dict(text="Динамика прибыли по каналам и периодам", font=dict(size=20, color="#1a1a1a", family="Arial Black")),
        xaxis_title=dict(text="Период (когорта)", font=dict(size=16, color="#1a1a1a", family="Arial")),
        yaxis_title=dict(text="Прибыль", font=dict(size=16, color="#1a1a1a", family="Arial")),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=14, color="#1a1a1a")
        ),
        hovermode="x unified",
        margin=dict(t=100, b=100, l=80, r=180),
        plot_bgcolor="rgba(255,255,255,0.9)",
        paper_bgcolor="white",
        font=dict(size=14, color="#1a1a1a", family="Arial")
    )

    fig.update_xaxes(tickfont=dict(size=14, color="#1a1a1a"), tickangle=45)
    fig.update_yaxes(tickfont=dict(size=14, color="#1a1a1a"))

    return fig