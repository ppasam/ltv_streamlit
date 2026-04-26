"""Analysis module for LTV data analysis."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd


def calculate_overall_metrics(df: pd.DataFrame) -> Dict:
    """Calculate overall sales metrics."""
    if df.empty:
        return {
            "total_revenue": 0,
            "total_orders": 0,
            "unique_customers": 0,
            "average_order_value": 0,
            "date_range": (None, None)
        }

    total_revenue = df["Revenue"].sum() if "Revenue" in df.columns else 0
    total_orders = len(df)
    unique_customers = df["Customer ID"].nunique() if "Customer ID" in df.columns else 0
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "unique_customers": unique_customers,
        "average_order_value": average_order_value,
        "date_range": (df["Date"].min(), df["Date"].max())
    }


def calculate_rfm_metrics(df: pd.DataFrame,
                          reference_date: Optional[datetime] = None) -> pd.DataFrame:
    """Calculate RFM (Recency, Frequency, Monetary) metrics for each customer."""
    if df.empty or "Customer ID" not in df.columns:
        return pd.DataFrame()

    if reference_date is None:
        reference_date = df["Date"].max() + timedelta(days=1)

    rfm = df.groupby("Customer ID").agg(
        Recency=("Date", lambda x: (reference_date - x.max()).days),
        Frequency=("Revenue", "count"),
        Monetary=("Revenue", "sum")
    ).reset_index()

    return rfm


def create_rfm_segments(rfm_df: pd.DataFrame) -> pd.DataFrame:
    """Create RFM segments based on quartiles."""
    if rfm_df.empty:
        return rfm_df

    rfm_df = rfm_df.copy()

    rfm_df["R_Score"] = pd.qcut(rfm_df["Recency"], q=4, labels=[4, 3, 2, 1], duplicates="drop")
    rfm_df["F_Score"] = pd.qcut(rfm_df["Frequency"].rank(method="first"), q=4, labels=[1, 2, 3, 4])
    rfm_df["M_Score"] = pd.qcut(rfm_df["Monetary"].rank(method="first"), q=4, labels=[1, 2, 3, 4])

    rfm_df["R_Score"] = rfm_df["R_Score"].astype(int)
    rfm_df["F_Score"] = rfm_df["F_Score"].astype(int)
    rfm_df["M_Score"] = rfm_df["M_Score"].astype(int)

    rfm_df["RFM_Score"] = rfm_df["R_Score"] + rfm_df["F_Score"] + rfm_df["M_Score"]

    return rfm_df


def calculate_cohort_retention(df: pd.DataFrame,
                               cohort_type: str,
                               cohort_size: int) -> pd.DataFrame:
    """Calculate cohort retention matrix."""
    if df.empty or "Customer ID" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    if cohort_type == "Количество месяцев":
        df["cohort_date"] = df["Date"].dt.to_period("M").dt.to_timestamp()
        df["period_number"] = ((df["Date"].dt.year - df["cohort_date"].dt.year) * 12 +
                               (df["Date"].dt.month - df["cohort_date"].dt.month))
    else:
        df["cohort_date"] = df["Date"] - pd.to_timedelta(df["Date"].dt.dayofweek, unit='D')
        df["period_number"] = ((df["Date"] - df["cohort_date"]).dt.days // 7)

    cohort_data = df.groupby(["cohort_date", "period_number"])["Customer ID"].nunique().reset_index()
    cohort_data.columns = ["cohort_date", "period_number", "num_customers"]

    cohort_sizes = cohort_data[cohort_data["period_number"] == 0][["cohort_date", "num_customers"]]
    cohort_sizes.columns = ["cohort_date", "cohort_size"]

    cohort_data = cohort_data.merge(cohort_sizes, on="cohort_date")
    cohort_data["retention"] = cohort_data["num_customers"] / cohort_data["cohort_size"] * 100

    retention_pivot = cohort_data.pivot(index="cohort_date", columns="period_number", values="retention")

    return retention_pivot


def calculate_customer_lifetime_value(df: pd.DataFrame,
                                      time_period_days: int = 365) -> pd.DataFrame:
    """Calculate customer LTV based on historical data."""
    if df.empty or "Customer ID" not in df.columns:
        return pd.DataFrame()

    reference_date = df["Date"].max()

    customer_data = df.groupby("Customer ID").agg({
        "Date": ["min", "max", "count"],
        "Revenue": "sum"
    }).reset_index()

    customer_data.columns = ["Customer ID", "first_purchase", "last_purchase", "num_purchases", "total_revenue"]

    customer_data["customer_lifetime_days"] = (customer_data["last_purchase"] - customer_data["first_purchase"]).dt.days

    customer_data["ltv"] = customer_data["total_revenue"]

    avg_order_value = customer_data["total_revenue"].sum() / customer_data["num_purchases"].sum()
    purchase_frequency = customer_data["num_purchases"].mean()

    customer_data["predicted_ltv"] = avg_order_value * purchase_frequency * time_period_days / 365

    return customer_data


def get_top_customers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Get top N customers by revenue."""
    if df.empty or "Customer ID" not in df.columns:
        return pd.DataFrame()

    top_customers = df.groupby("Customer ID")["Revenue"].sum().reset_index()
    top_customers = top_customers.sort_values("Revenue", ascending=False).head(n)
    top_customers.columns = ["Customer ID", "Total Revenue"]

    return top_customers


def get_sales_by_period(df: pd.DataFrame, period: str = "month") -> pd.DataFrame:
    """Get sales aggregated by time period."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    if period == "day":
        df["period"] = df["Date"].dt.date
    elif period == "week":
        df["period"] = df["Date"].dt.to_period("W").dt.start_time
    elif period == "month":
        df["period"] = df["Date"].dt.to_period("M").dt.start_time
    elif period == "year":
        df["period"] = df["Date"].dt.to_period("Y").dt.start_time
    else:
        df["period"] = df["Date"].dt.to_period("M").dt.start_time

    sales_by_period = df.groupby("period").agg({
        "Revenue": "sum",
        "Customer ID": "nunique"
    }).reset_index()

    sales_by_period.columns = ["period", "revenue", "unique_customers"]

    return sales_by_period