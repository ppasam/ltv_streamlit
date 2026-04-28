"""Analysis module for LTV data analysis."""
from datetime import datetime, timedelta
from typing import List, Tuple

import pandas as pd


def calculate_overall_metrics(
    sales_df: pd.DataFrame,
    promotion_df: pd.DataFrame,
    marketing_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate overall metrics for the dashboard."""
    unique_customers = sales_df["Customer ID"].nunique() if "Customer ID" in sales_df.columns else 0
    num_orders = len(sales_df) if not sales_df.empty else 0

    period_start = sales_df["Date"].min() if "Date" in sales_df.columns and not sales_df.empty else None
    period_end = sales_df["Date"].max() if "Date" in sales_df.columns and not sales_df.empty else None
    period_start_str = period_start.strftime('%Y-%m-%d') if period_start else "N/A"
    period_end_str = period_end.strftime('%Y-%m-%d') if period_end else "N/A"
    avg_orders_per_customer = round(num_orders / unique_customers, 2) if unique_customers > 0 else 0
    max_orders_per_customer = sales_df.groupby("Customer ID").size().max() if "Customer ID" in sales_df.columns and not sales_df.empty else 0
    avg_order_price = f"${round(sales_df['Revenue'].mean(), 2):,.2f}" if "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    min_order_price = f"${sales_df['Revenue'].min():,.2f}" if "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    max_order_price = f"${sales_df['Revenue'].max():,.2f}" if "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    min_revenue_per_customer = f"${sales_df.groupby('Customer ID')['Revenue'].sum().min():,.2f}" if "Customer ID" in sales_df.columns and "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    max_revenue_per_customer = f"${sales_df.groupby('Customer ID')['Revenue'].sum().max():,.2f}" if "Customer ID" in sales_df.columns and "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    total_revenue = sales_df["Revenue"].sum() if "Revenue" in sales_df.columns and not sales_df.empty else 0
    total_cost = sales_df["cost"].sum() if "cost" in sales_df.columns and not sales_df.empty else 0
    avg_margin = f"{(total_revenue / total_cost - 1) * 100:.2f}%" if total_cost > 0 else "0.00%"

    total_revenue_str = f"${total_revenue:,.2f}"
    total_cost_str = f"${total_cost:,.2f}"
    gross_profit = f"${(total_revenue - total_cost):,.2f}"
    gross_margin = f"{((total_revenue - total_cost) / total_revenue * 100):.2f}%" if total_revenue > 0 else "0.00%"

    acquisition_costs_val = promotion_df["costs"].sum() if not promotion_df.empty and "costs" in promotion_df.columns else 0
    acquisition_costs = f"${acquisition_costs_val:,.2f}"

    other_costs_val = marketing_df["costs"].sum() if not marketing_df.empty and "costs" in marketing_df.columns else 0
    other_costs = f"${other_costs_val:,.2f}"

    profit_val = total_revenue - total_cost - acquisition_costs_val - other_costs_val
    profit = f"${profit_val:,.2f}"
    margin = f"{(profit_val / total_revenue * 100):.2f}%" if total_revenue > 0 else "0.00%"

    metrics_data = {
        "Показатель": [
            "Количество уникальных клиентов", "Начало периода", "Конец периода",
            "Количество заказов", "В среднем заказов на 1 клиента", "Максимально заказов на 1 клиента",
            "Средняя цена заказа", "Минимальная цена заказа", "Максимальная цена заказа",
            "Минимальная сумма заказов на 1 клиента", "Максимальная сумма заказов на 1 клиента",
            "Выручка", "Себестоимость продаж", "Средняя наценка",
            "Валовая прибыль", "Валовая маржа", "Затраты на привлечение клиентов",
            "Прочие затраты", "Прибыль", "Маржа"
        ],
        "Значение": [
            unique_customers, period_start_str, period_end_str,
            num_orders, avg_orders_per_customer, max_orders_per_customer,
            avg_order_price, min_order_price, max_order_price,
            min_revenue_per_customer, max_revenue_per_customer,
            total_revenue_str, total_cost_str, avg_margin,
            gross_profit, gross_margin, acquisition_costs,
            other_costs, profit, margin
        ]
    }
    return pd.DataFrame(metrics_data)


def calculate_cohort_columns(
    cohort_dates: List[datetime],
    num_cohorts: int,
    cohort_size: int,
    is_days: bool
) -> List[str]:
    """Calculate cohort column labels."""
    cohort_columns = []
    for i, cohort_date in enumerate(cohort_dates):
        if i < num_cohorts - 1:
            end_date = cohort_dates[i + 1] - timedelta(days=1)
        else:
            if is_days:
                end_date = cohort_date + timedelta(days=cohort_size - 1)
            else:
                next_month = cohort_date.month + cohort_size
                next_year = cohort_date.year + (next_month - 1) // 12
                next_month = ((next_month - 1) % 12) + 1
                end_date = cohort_date.replace(year=next_year, month=next_month) - timedelta(days=1)
        cohort_columns.append(end_date.strftime('%Y-%m-%d'))
    return cohort_columns


def calculate_costs_table(
    df: pd.DataFrame,
    cohort_dates: List[datetime],
    num_cohorts: int,
    cohort_size: int,
    is_days: bool
) -> pd.DataFrame:
    """Calculate costs table by channel and cohort."""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["period_end"] = pd.to_datetime(df["period_end"])

    cohort_columns = calculate_cohort_columns(cohort_dates, num_cohorts, cohort_size, is_days)
    table_data = {}

    for channel in df["channels"].unique():
        table_data[channel] = [0] * num_cohorts

    for _, row in df.iterrows():
        channel = row["channels"]
        period_date = row["period_end"]
        cost = row["costs"]

        for i, cohort_date in enumerate(cohort_dates):
            if i < num_cohorts - 1:
                next_cohort_date = cohort_dates[i + 1]
            else:
                if is_days:
                    next_cohort_date = cohort_date + timedelta(days=cohort_size)
                else:
                    next_month = cohort_date.month + cohort_size
                    next_year = cohort_date.year + (next_month - 1) // 12
                    next_month = ((next_month - 1) % 12) + 1
                    next_cohort_date = cohort_date.replace(year=next_year, month=next_month)

            if cohort_date <= period_date < next_cohort_date:
                if channel in table_data:
                    table_data[channel][i] += cost
                break

    table_df = pd.DataFrame(table_data, index=cohort_columns).T
    table_df["ВСЕГО"] = table_df.sum(axis=1)

    totals_row = table_df.sum()
    totals_row.name = "ИТОГО"
    table_df = pd.concat([table_df, totals_row.to_frame().T])

    return table_df


def calculate_promotion_costs_table(
    promotion_df: pd.DataFrame,
    cohort_dates: List[datetime],
    num_cohorts: int,
    cohort_size: int,
    is_days: bool
) -> pd.DataFrame:
    """Calculate promotion costs table."""
    if not promotion_df.empty:
        if "period_end" in promotion_df.columns and "channels" in promotion_df.columns and "costs" in promotion_df.columns:
            return calculate_costs_table(promotion_df, cohort_dates, num_cohorts, cohort_size, is_days)
    return pd.DataFrame()


def calculate_marketing_costs_table(
    marketing_df: pd.DataFrame,
    cohort_dates: List[datetime],
    num_cohorts: int,
    cohort_size: int,
    is_days: bool
) -> pd.DataFrame:
    """Calculate marketing costs table."""
    if not marketing_df.empty:
        if "period_end" in marketing_df.columns and "channels" in marketing_df.columns and "costs" in marketing_df.columns:
            return calculate_costs_table(marketing_df, cohort_dates, num_cohorts, cohort_size, is_days)
    return pd.DataFrame()