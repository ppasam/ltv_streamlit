"""Plotting module for LTV analysis visualizations."""
import re
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


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert hex or rgb color to rgba string."""
    hex_color = hex_color.strip()
    if hex_color.startswith("rgb"):
        rgb_match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", hex_color)
        if rgb_match:
            r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        else:
            return f"rgba(128,128,128,{alpha})"
    elif hex_color.startswith("#") and len(hex_color) == 7:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
    else:
        return f"rgba(128,128,128,{alpha})"
    return f"rgba({r},{g},{b},{alpha})"


def create_cohort_revenue_chart(revenue_df: pd.DataFrame) -> go.Figure:
    """Create stacked area chart for cohort revenue dynamics."""
    if revenue_df.empty:
        return None

    revenue_df = revenue_df.copy()

    if "Когорты" in revenue_df.columns:
        revenue_df = revenue_df.set_index("Когорты")

    if "ВСЕГО" in revenue_df.columns:
        revenue_df = revenue_df.drop(columns=["ВСЕГО"])

    columns = [col for col in revenue_df.columns if col != "ВСЕГО"]
    cohorts = list(revenue_df.index)

    if not cohorts or not columns:
        return None

    fig = go.Figure()

    colors = px.colors.qualitative.Set1 + px.colors.qualitative.Set2 + px.colors.qualitative.Dark24

    for i, cohort in enumerate(cohorts):
        values = []
        for col in columns:
            val = revenue_df.loc[cohort, col]
            if isinstance(val, str):
                val = val.strip()
                if val == "" or val == "$":
                    val = 0.0
                else:
                    val = float(val.replace("$", "").replace(",", ""))
            values.append(val)

        color = colors[i % len(colors)]
        fillcolor = hex_to_rgba(color, 0.6)
        fig.add_trace(go.Scatter(
            x=columns,
            y=values,
            name=cohort,
            stackgroup="cohort_revenue",
            fillcolor=fillcolor,
            line=dict(width=2, color=colors[i % len(colors)]),
            mode="lines"
        ))

    fig.update_layout(
        title=dict(text="Сумма выручки по когортам клиентов", font=dict(size=20, color="#1a1a1a", family="Arial Black")),
        xaxis_title=dict(text="Период (когорта)", font=dict(size=16, color="#1a1a1a", family="Arial")),
        yaxis_title=dict(text="Выручка", font=dict(size=16, color="#1a1a1a", family="Arial")),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=12, color="#1a1a1a")
        ),
        hovermode="x unified",
        margin=dict(t=100, b=80, l=80, r=180),
        plot_bgcolor="rgba(255,255,255,0.9)",
        paper_bgcolor="white",
        font=dict(size=14, color="#1a1a1a", family="Arial")
    )

    fig.update_xaxes(tickfont=dict(size=14, color="#1a1a1a"), tickangle=45)
    fig.update_yaxes(tickfont=dict(size=14, color="#1a1a1a"))

    return fig


def create_client_index_chart(index_df: pd.DataFrame) -> go.Figure:
    """Create line chart for client retention index."""
    if index_df.empty:
        return None

    index_df = index_df.copy()

    if "Когорты" in index_df.columns:
        index_df = index_df.set_index("Когорты")

    cohorts = list(index_df.index)
    columns = list(index_df.columns)

    if not cohorts or not columns:
        return None

    fig = go.Figure()

    colors = px.colors.qualitative.Set1 + px.colors.qualitative.Set2 + px.colors.qualitative.Dark24

    for i, cohort in enumerate(cohorts):
        values = []
        for col in columns:
            val = index_df.loc[cohort, col]
            if isinstance(val, str) and val.strip() == "":
                values.append(None)
            else:
                values.append(float(val))
        values = [v if v is not None and v > 0 else None for v in values]

        fig.add_trace(go.Scatter(
            x=columns,
            y=values,
            name=cohort,
            mode="lines+markers",
            line=dict(width=2, color=colors[i % len(colors)]),
            marker=dict(size=8, symbol="circle")
        ))

    fig.update_layout(
        title=dict(text="Индекс активных клиентов", font=dict(size=20, color="#1a1a1a", family="Arial Black")),
        xaxis_title=dict(text="Период", font=dict(size=16, color="#1a1a1a", family="Arial")),
        yaxis_title=dict(text="Индекс", font=dict(size=16, color="#1a1a1a", family="Arial")),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=12, color="#1a1a1a")
        ),
        hovermode="x unified",
        margin=dict(t=100, b=80, l=80, r=200),
        plot_bgcolor="rgba(255,255,255,0.9)",
        paper_bgcolor="white",
        font=dict(size=14, color="#1a1a1a", family="Arial")
    )

    fig.update_xaxes(tickfont=dict(size=14, color="#1a1a1a"), tickangle=45)
    fig.update_yaxes(tickfont=dict(size=14, color="#1a1a1a"), range=[0, 1.1])

    return fig