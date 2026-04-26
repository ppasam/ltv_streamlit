"""Plotting module for LTV analysis visualizations."""
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def plot_revenue_trend(sales_by_period: pd.DataFrame) -> go.Figure:
    """Plot revenue trend over time."""
    if sales_by_period.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    fig = px.line(sales_by_period, x="period", y="revenue",
                  title="Revenue Over Time",
                  labels={"period": "Period", "revenue": "Revenue"})
    fig.update_traces(mode="lines+markers")
    return fig


def plot_customer_count_trend(sales_by_period: pd.DataFrame) -> go.Figure:
    """Plot unique customer count over time."""
    if sales_by_period.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    fig = px.line(sales_by_period, x="period", y="unique_customers",
                  title="Unique Customers Over Time",
                  labels={"period": "Period", "unique_customers": "Unique Customers"})
    fig.update_traces(mode="lines+markers")
    return fig


def plot_top_customers(top_customers: pd.DataFrame) -> go.Figure:
    """Plot top customers by revenue."""
    if top_customers.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    fig = px.bar(top_customers, x="Customer ID", y="Total Revenue",
                 title="Top Customers by Revenue",
                 labels={"Customer ID": "Customer", "Total Revenue": "Revenue"})
    fig.update_layout(xaxis_tickangle=-45)
    return fig


def plot_rfm_scatter(rfm_df: pd.DataFrame) -> go.Figure:
    """Plot RFM scatter plot."""
    if rfm_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    fig = px.scatter(rfm_df, x="Recency", y="Monetary",
                      size="Frequency", color="RFM_Score",
                      title="RFM Analysis",
                      labels={"Recency": "Recency (days)",
                              "Monetary": "Monetary ($)",
                              "Frequency": "Frequency",
                              "RFM_Score": "RFM Score"})
    return fig


def plot_rfm_histogram(rfm_df: pd.DataFrame, column: str) -> go.Figure:
    """Plot RFM score distribution."""
    if rfm_df.empty or column not in rfm_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    fig = px.histogram(rfm_df, x=column, title=f"{column} Distribution")
    return fig


def plot_cohort_heatmap(retention_df: pd.DataFrame) -> go.Figure:
    """Plot cohort retention heatmap."""
    if retention_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    retention_df.index = retention_df.index.strftime("%Y-%m")

    fig = px.imshow(retention_df,
                    labels=dict(x="Period", y="Cohort", color="Retention (%)"),
                    title="Cohort Retention Heatmap",
                    color_continuous_scale="Blues",
                    text_auto=".1f")
    fig.update_layout(xaxis_title="Period Number", yaxis_title="Cohort")
    return fig


def plot_rfm_segmentation(rfm_df: pd.DataFrame) -> go.Figure:
    """Plot RFM segment distribution."""
    if rfm_df.empty or "RFM_Score" not in rfm_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    segment_counts = rfm_df["RFM_Score"].value_counts().reset_index()
    segment_counts.columns = ["RFM_Score", "Count"]

    fig = px.bar(segment_counts, x="RFM_Score", y="Count",
                 title="RFM Score Distribution",
                 labels={"RFM_Score": "RFM Score", "Count": "Number of Customers"})
    return fig


def plot_revenue_by_customer_lifetime(customer_ltv: pd.DataFrame) -> go.Figure:
    """Plot revenue by customer lifetime."""
    if customer_ltv.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    fig = px.scatter(customer_ltv, x="customer_lifetime_days", y="total_revenue",
                     size="num_purchases", title="Customer Lifetime vs Revenue",
                     labels={"customer_lifetime_days": "Customer Lifetime (days)",
                             "total_revenue": "Total Revenue",
                             "num_purchases": "Number of Purchases"})
    return fig


def plot_average_order_value_trend(sales_by_period: pd.DataFrame) -> go.Figure:
    """Plot average order value over time."""
    if sales_by_period.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    sales_by_period = sales_by_period.copy()
    sales_by_period["avg_order_value"] = sales_by_period["revenue"] / sales_by_period["unique_customers"]

    fig = px.line(sales_by_period, x="period", y="avg_order_value",
                  title="Average Order Value Over Time",
                  labels={"period": "Period", "avg_order_value": "Avg Order Value"})
    fig.update_traces(mode="lines+markers")
    return fig