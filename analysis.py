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


def calculate_revenue_table(sales_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate revenue table by channel and cohort date range."""
    if sales_df.empty or cohorts_df.empty:
        return pd.DataFrame()
    
    if "Date" not in sales_df.columns or "Revenue" not in sales_df.columns:
        return pd.DataFrame()
    
    if "acquisition_channel" not in sales_df.columns:
        return pd.DataFrame()
    
    sales_df = sales_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(sales_df["Date"]):
        sales_df["Date"] = pd.to_datetime(sales_df["Date"])
    
    cohorts_sorted = cohorts_df.sort_values("date_start")
    cohorts_sorted = cohorts_sorted.copy()
    cohorts_sorted["date_start"] = pd.to_datetime(cohorts_sorted["date_start"])
    cohorts_sorted["date_end"] = pd.to_datetime(cohorts_sorted["date_end"])
    
    channels = sorted(sales_df["acquisition_channel"].dropna().unique())
    
    table_data = {}
    for channel in channels:
        channel_sales = sales_df[sales_df["acquisition_channel"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            date_start = coh_row["date_start"]
            date_end = coh_row["date_end"]
            col_header = date_end.strftime('%Y-%m-%d') if hasattr(date_end, 'strftime') else str(date_end)
            
            cohort_sales = channel_sales[(channel_sales["Date"] >= date_start) & (channel_sales["Date"] <= date_end)]
            row_data[col_header] = cohort_sales["Revenue"].sum()
        
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data
    
    if not table_data:
        return pd.DataFrame()
    
    revenue_df = pd.DataFrame(table_data).T
    
    totals_row = revenue_df.sum()
    totals_row.name = "ИТОГО"
    revenue_df = pd.concat([revenue_df, totals_row.to_frame().T])
    
    return revenue_df


def calculate_cost_table(sales_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate cost table by channel and cohort date range."""
    if sales_df.empty or cohorts_df.empty:
        return pd.DataFrame()
    
    if "Date" not in sales_df.columns or "cost" not in sales_df.columns:
        return pd.DataFrame()
    
    if "acquisition_channel" not in sales_df.columns:
        return pd.DataFrame()
    
    sales_df = sales_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(sales_df["Date"]):
        sales_df["Date"] = pd.to_datetime(sales_df["Date"])
    
    cohorts_sorted = cohorts_df.sort_values("date_start")
    cohorts_sorted = cohorts_sorted.copy()
    cohorts_sorted["date_start"] = pd.to_datetime(cohorts_sorted["date_start"])
    cohorts_sorted["date_end"] = pd.to_datetime(cohorts_sorted["date_end"])
    
    channels = sorted(sales_df["acquisition_channel"].dropna().unique())
    
    table_data = {}
    for channel in channels:
        channel_sales = sales_df[sales_df["acquisition_channel"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            date_start = coh_row["date_start"]
            date_end = coh_row["date_end"]
            col_header = date_end.strftime('%Y-%m-%d') if hasattr(date_end, 'strftime') else str(date_end)
            
            cohort_sales = channel_sales[(channel_sales["Date"] >= date_start) & (channel_sales["Date"] <= date_end)]
            row_data[col_header] = cohort_sales["cost"].sum()
        
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data
    
    if not table_data:
        return pd.DataFrame()
    
    cost_df = pd.DataFrame(table_data).T
    
    totals_row = cost_df.sum()
    totals_row.name = "ИТОГО"
    cost_df = pd.concat([cost_df, totals_row.to_frame().T])
    
    return cost_df


def calculate_promotion_costs_table(promotion_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate promotion costs table by channel and cohort."""
    if promotion_df.empty or "cohort" not in promotion_df.columns:
        return pd.DataFrame()
    
    promotion_with_cohort = promotion_df[promotion_df["cohort"] != ""]
    
    if promotion_with_cohort.empty:
        return pd.DataFrame()
    
    if "costs" not in promotion_with_cohort.columns:
        return pd.DataFrame()
    
    cohorts_sorted = cohorts_df.sort_values("date_start")
    channels = sorted(promotion_with_cohort["channels"].dropna().unique())
    
    table_data = {}
    for channel in channels:
        channel_costs = promotion_with_cohort[promotion_with_cohort["channels"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            cohort_name = coh_row["cohort"]
            date_end = coh_row["date_end"]
            col_header = date_end.strftime('%Y-%m-%d') if hasattr(date_end, 'strftime') else str(date_end)
            
            cohort_costs = channel_costs[channel_costs["cohort"] == cohort_name]
            row_data[col_header] = cohort_costs["costs"].sum()
        
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data
    
    if not table_data:
        return pd.DataFrame()
    
    promotion_df_result = pd.DataFrame(table_data).T
    
    totals_row = promotion_df_result.sum()
    totals_row.name = "ИТОГО"
    promotion_df_result = pd.concat([promotion_df_result, totals_row.to_frame().T])
    
    return promotion_df_result


def calculate_other_marketing_costs_table(marketing_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate other marketing costs table by channel and cohort."""
    if marketing_df.empty or "cohort" not in marketing_df.columns:
        return pd.DataFrame()
    
    marketing_with_cohort = marketing_df[marketing_df["cohort"] != ""]
    
    if marketing_with_cohort.empty:
        return pd.DataFrame()
    
    if "costs" not in marketing_with_cohort.columns:
        return pd.DataFrame()
    
    cohorts_sorted = cohorts_df.sort_values("date_start")
    channels = sorted(marketing_with_cohort["channels"].dropna().unique())
    
    table_data = {}
    for channel in channels:
        channel_costs = marketing_with_cohort[marketing_with_cohort["channels"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            cohort_name = coh_row["cohort"]
            date_end = coh_row["date_end"]
            col_header = date_end.strftime('%Y-%m-%d') if hasattr(date_end, 'strftime') else str(date_end)
            
            cohort_costs = channel_costs[channel_costs["cohort"] == cohort_name]
            row_data[col_header] = cohort_costs["costs"].sum()
        
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data
    
    if not table_data:
        return pd.DataFrame()
    
    marketing_df_result = pd.DataFrame(table_data).T
    
    totals_row = marketing_df_result.sum()
    totals_row.name = "ИТОГО"
    marketing_df_result = pd.concat([marketing_df_result, totals_row.to_frame().T])
    
    return marketing_df_result


def calculate_profit_table(revenue_df: pd.DataFrame, cost_df: pd.DataFrame, 
                          promotion_df: pd.DataFrame, marketing_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate profit table as Revenue - Cost - Promotion Costs - Other Marketing Costs."""
    if revenue_df.empty:
        return pd.DataFrame()
    
    all_columns = list(revenue_df.columns)
    channels = list(revenue_df.index)
    
    if "ИТОГО" in channels:
        channels = channels[:-1]
    
    table_data = {}
    for channel in channels:
        row_data = {}
        for col in all_columns:
            revenue_val = revenue_df.loc[channel, col] if col in revenue_df.columns else 0
            cost_val = cost_df.loc[channel, col] if col in cost_df.columns and channel in cost_df.index else 0
            promo_val = promotion_df.loc[channel, col] if col in promotion_df.columns and channel in promotion_df.index else 0
            marketing_val = marketing_df.loc[channel, col] if col in marketing_df.columns and channel in marketing_df.index else 0
            
            row_data[col] = revenue_val - cost_val - promo_val - marketing_val
        
        table_data[channel] = row_data
    
    profit_df = pd.DataFrame(table_data).T
    
    totals_row = profit_df.sum()
    totals_row.name = "ИТОГО"
    profit_df = pd.concat([profit_df, totals_row.to_frame().T])
    
    return profit_df


def calculate_orders_table(sales_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate number of orders by channel and cohort date range."""
    if sales_df.empty or cohorts_df.empty:
        return pd.DataFrame()
    
    if "Date" not in sales_df.columns:
        return pd.DataFrame()
    
    if "acquisition_channel" not in sales_df.columns:
        return pd.DataFrame()
    
    sales_df = sales_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(sales_df["Date"]):
        sales_df["Date"] = pd.to_datetime(sales_df["Date"])
    
    cohorts_sorted = cohorts_df.sort_values("date_start")
    cohorts_sorted = cohorts_sorted.copy()
    cohorts_sorted["date_start"] = pd.to_datetime(cohorts_sorted["date_start"])
    cohorts_sorted["date_end"] = pd.to_datetime(cohorts_sorted["date_end"])
    
    channels = sorted(sales_df["acquisition_channel"].dropna().unique())
    
    table_data = {}
    for channel in channels:
        channel_sales = sales_df[sales_df["acquisition_channel"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            date_start = coh_row["date_start"]
            date_end = coh_row["date_end"]
            col_header = date_end.strftime('%Y-%m-%d') if hasattr(date_end, 'strftime') else str(date_end)
            
            cohort_sales = channel_sales[(channel_sales["Date"] >= date_start) & (channel_sales["Date"] <= date_end)]
            row_data[col_header] = cohort_sales.shape[0]
        
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data
    
    if not table_data:
        return pd.DataFrame()
    
    orders_df = pd.DataFrame(table_data).T
    
    totals_row = orders_df.sum()
    totals_row.name = "ИТОГО"
    orders_df = pd.concat([orders_df, totals_row.to_frame().T])
    
    return orders_df


def calculate_avg_profit_per_order_table(profit_table: pd.DataFrame, orders_table: pd.DataFrame) -> pd.DataFrame:
    """Calculate average profit per order as Profit / Orders."""
    if profit_table.empty or orders_table.empty:
        return pd.DataFrame()
    
    result = orders_table.astype(float).copy()
    
    for col in result.columns:
        for idx in result.index:
            profit_val = profit_table.loc[idx, col] if idx in profit_table.index and col in profit_table.columns else 0
            orders_val = orders_table.loc[idx, col] if idx in orders_table.index else 0
            
            if orders_val != 0:
                result.loc[idx, col] = profit_val / orders_val
            else:
                result.loc[idx, col] = 0
    
    return result


def calculate_profit_by_channel_table(profit_table: pd.DataFrame) -> pd.DataFrame:
    """Calculate profit by channel with share percentage."""
    if profit_table.empty:
        return pd.DataFrame()
    
    if "ВСЕГО" not in profit_table.columns:
        return pd.DataFrame()
    
    channels = [idx for idx in profit_table.index if idx != "ИТОГО"]
    
    profit_values = []
    for channel in channels:
        profit_val = profit_table.loc[channel, "ВСЕГО"] if "ВСЕГО" in profit_table.columns else 0
        profit_values.append(profit_val)
    
    total_profit = sum(profit_values)
    
    table_data = []
    for i, channel in enumerate(channels):
        profit_val = profit_values[i]
        share = round((profit_val / total_profit) * 100, 2) if total_profit != 0 else 0
        table_data.append({
            "Канал": channel,
            "Сумма": profit_val,
            "Доля": f"{share}%"
        })
    
    table_data.append({
        "Канал": "ИТОГО",
        "Сумма": total_profit,
        "Доля": "100%"
    })
    
    return pd.DataFrame(table_data)


def calculate_avg_acquisition_cost_table(promotion_df: pd.DataFrame, orders_table: pd.DataFrame) -> pd.DataFrame:
    """Calculate average acquisition cost per order as Promotion Costs / Orders."""
    if orders_table.empty:
        return pd.DataFrame()
    
    result = orders_table.astype(float).copy()
    
    promotion_df = promotion_df.copy() if not promotion_df.empty else pd.DataFrame()
    
    for col in result.columns:
        for idx in result.index:
            promo_val = promotion_df.loc[idx, col] if idx in promotion_df.index and col in promotion_df.columns else 0
            orders_val = orders_table.loc[idx, col] if idx in orders_table.index else 0
            
            if orders_val != 0:
                result.loc[idx, col] = promo_val / orders_val
            else:
                result.loc[idx, col] = 0
    
    return result