"""Analysis module for LTV data analysis."""
from datetime import datetime, date
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


def calculate_promotion_costs_table(promotion_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate promotion costs table by channel and cohort date ranges."""
    if promotion_df.empty or cohorts_df.empty:
        return pd.DataFrame()
    
    if "expenses_date" not in promotion_df.columns or "channels" not in promotion_df.columns or "costs" not in promotion_df.columns:
        return pd.DataFrame()
    
    cohorts_sorted = cohorts_df.sort_values("date_start")
    channels = sorted(promotion_df["channels"].dropna().unique())
    
    table_data = {}
    for channel in channels:
        channel_costs = promotion_df[promotion_df["channels"] == channel]
        row_data = {}
        
        for _, coh_row in cohorts_sorted.iterrows():
            date_start = coh_row["date_start"]
            date_end = coh_row["date_end"]
            col_header = date_end.strftime('%Y-%m-%d') if hasattr(date_end, 'strftime') else str(date_end)
            
            if isinstance(date_start, str):
                date_start = datetime.strptime(date_start.split(' ')[0], '%Y-%m-%d').date()
            else:
                date_start = date_start.date() if hasattr(date_start, 'date') else date_start
            
            if isinstance(date_end, str):
                date_end = datetime.strptime(date_end.split(' ')[0], '%Y-%m-%d').date()
            else:
                date_end = date_end.date() if hasattr(date_end, 'date') else date_end
            
            filtered = channel_costs[
                channel_costs["expenses_date"].apply(
                    lambda x: (
                        (d := datetime.strptime(str(x).split(' ')[0], '%Y-%m-%d').date()) 
                        if isinstance(x, str) else 
                        (x.date() if hasattr(x, 'date') else x)
                    ) >= date_start and 
                    (d if isinstance(d, date) else d) <= date_end
                    if x else False
                ) if channel_costs["expenses_date"].notna().any() else False
            ]
            
            total = 0
            for _, row in channel_costs.iterrows():
                exp_date = row["expenses_date"]
                if not exp_date:
                    continue
                try:
                    if isinstance(exp_date, str):
                        exp_date_dt = datetime.strptime(exp_date.split(' ')[0], '%Y-%m-%d').date()
                    else:
                        exp_date_dt = exp_date.date() if hasattr(exp_date, 'date') else exp_date
                    
                    if date_start <= exp_date_dt <= date_end:
                        total += row["costs"] if row["costs"] else 0
                except:
                    continue
            
            row_data[col_header] = total
        
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data
    
    if not table_data:
        return pd.DataFrame()
    
    costs_df = pd.DataFrame(table_data).T
    
    totals_row = costs_df.sum()
    totals_row.name = "ИТОГО"
    costs_df = pd.concat([costs_df, totals_row.to_frame().T])
    
    return costs_df


def calculate_revenue_table(sales_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate revenue table by channel and cohort."""
    if sales_df.empty or "cohort" not in sales_df.columns:
        return pd.DataFrame()
    
    sales_with_cohort = sales_df[sales_df["cohort"] != ""]
    
    if sales_with_cohort.empty:
        return pd.DataFrame()
    
    cohorts_sorted = cohorts_df.sort_values("date_start")
    channels = sorted(sales_with_cohort["acquisition_channel"].dropna().unique())
    
    table_data = {}
    for channel in channels:
        channel_sales = sales_with_cohort[sales_with_cohort["acquisition_channel"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            cohort_name = coh_row["cohort"]
            date_end = coh_row["date_end"]
            col_header = date_end.strftime('%Y-%m-%d') if hasattr(date_end, 'strftime') else str(date_end)
            
            cohort_sales = channel_sales[channel_sales["cohort"] == cohort_name]
            row_data[col_header] = cohort_sales["Revenue"].sum() if "Revenue" in cohort_sales.columns else 0
        
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data
    
    if not table_data:
        return pd.DataFrame()
    
    revenue_df = pd.DataFrame(table_data).T
    
    totals_row = revenue_df.sum()
    totals_row.name = "ИТОГО"
    revenue_df = pd.concat([revenue_df, totals_row.to_frame().T])
    
    return revenue_df