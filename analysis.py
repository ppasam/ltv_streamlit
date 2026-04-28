"""Analysis module for LTV data analysis."""
from datetime import datetime
from typing import Optional

import pandas as pd


def calculate_overall_metrics(
    sales_df: pd.DataFrame,
    promotion_df: pd.DataFrame,
    marketing_df: pd.DataFrame,
    clients_df: pd.DataFrame = None
) -> pd.DataFrame:
    """Calculate overall metrics for the dashboard."""
    if "cohort" in sales_df.columns:
        sales_df = sales_df[sales_df["cohort"] != ""]
    
    unique_customers = sales_df["Customer ID"].nunique() if "Customer ID" in sales_df.columns else 0
    num_orders = len(sales_df) if not sales_df.empty else 0

    period_start = sales_df["Date"].min() if "Date" in sales_df.columns and not sales_df.empty else None
    period_end = sales_df["Date"].max() if "Date" in sales_df.columns and not sales_df.empty else None
    period_start_str = period_start.strftime('%Y-%m-%d') if period_start else "N/A"
    period_end_str = period_end.strftime('%Y-%m-%d') if period_end else "N/A"
    avg_orders_per_customer = round(num_orders / unique_customers, 2) if unique_customers > 0 else 0
    
    if clients_df is not None and "num_orders" in clients_df.columns:
        clients_with_cohort = clients_df[clients_df["cohort"] != ""]
        max_orders_per_customer = int(clients_with_cohort["num_orders"].max()) if not clients_with_cohort.empty else 0
    else:
        max_orders_per_customer = sales_df.groupby("Customer ID").size().max() if "Customer ID" in sales_df.columns and not sales_df.empty else 0
    
    avg_order_price = f"${round(sales_df['Revenue'].mean(), 2):,.2f}" if "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    min_order_price = f"${sales_df['Revenue'].min():,.2f}" if "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    max_order_price = f"${sales_df['Revenue'].max():,.2f}" if "Revenue" in sales_df.columns and not sales_df.empty else "$0.00"
    
    if clients_df is not None and "total_amount" in clients_df.columns:
        clients_with_cohort = clients_df[clients_df["cohort"] != ""]
        min_revenue_per_customer = f"${clients_with_cohort['total_amount'].min():,.2f}" if not clients_with_cohort.empty else "$0.00"
        max_revenue_per_customer = f"${clients_with_cohort['total_amount'].max():,.2f}" if not clients_with_cohort.empty else "$0.00"
    else:
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