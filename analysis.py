"""Analysis module for LTV data analysis."""
import pandas as pd


def _prepare_cohorts(cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Sort cohorts and ensure date columns are datetime."""
    df = cohorts_df.sort_values("date_start").copy()
    for col in ["date_start", "date_end"]:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col])
    return df


def _add_totals_row(df: pd.DataFrame) -> pd.DataFrame:
    """Append an ИТОГО row to the DataFrame."""
    totals = df.sum(numeric_only=True)
    totals.name = "ИТОГО"
    return pd.concat([df, totals.to_frame().T])


def _build_sales_cohort_pivot(
    sales_df: pd.DataFrame,
    cohorts_df: pd.DataFrame,
    value_column: str,
    agg: str = "sum"
) -> pd.DataFrame:
    """Build a channel × cohort pivot table from sales data (revenue/cost/orders)."""
    if sales_df.empty or cohorts_df.empty:
        return pd.DataFrame()
    if "Date" not in sales_df.columns or "acquisition_channel" not in sales_df.columns:
        return pd.DataFrame()
    if value_column not in sales_df.columns:
        return pd.DataFrame()

    if "cohort" in sales_df.columns:
        sales_df = sales_df[sales_df["cohort"] != ""]

    sales_df = sales_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(sales_df["Date"]):
        sales_df["Date"] = pd.to_datetime(sales_df["Date"])

    cohorts_sorted = _prepare_cohorts(cohorts_df)
    channels = sorted(sales_df["acquisition_channel"].dropna().unique())

    table_data = {}
    for channel in channels:
        channel_sales = sales_df[sales_df["acquisition_channel"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            col_header = coh_row["date_end"].strftime('%Y-%m-%d')
            mask = (
                (channel_sales["Date"] >= coh_row["date_start"]) &
                (channel_sales["Date"] <= coh_row["date_end"])
            )
            if agg == "sum":
                row_data[col_header] = channel_sales.loc[mask, value_column].sum()
            else:
                row_data[col_header] = mask.sum()
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data

    if not table_data:
        return pd.DataFrame()

    result = pd.DataFrame(table_data).T
    return _add_totals_row(result)


def _build_expense_cohort_pivot(
    expense_df: pd.DataFrame,
    cohorts_df: pd.DataFrame
) -> pd.DataFrame:
    """Build a channel × cohort pivot from expense data (promotion/marketing)."""
    if expense_df.empty or "cohort" not in expense_df.columns:
        return pd.DataFrame()

    expense_df = expense_df[expense_df["cohort"] != ""]
    if expense_df.empty or "costs" not in expense_df.columns:
        return pd.DataFrame()

    cohorts_sorted = _prepare_cohorts(cohorts_df)
    channels = sorted(expense_df["channels"].dropna().unique())

    table_data = {}
    for channel in channels:
        channel_costs = expense_df[expense_df["channels"] == channel]
        row_data = {}
        for _, coh_row in cohorts_sorted.iterrows():
            col_header = coh_row["date_end"].strftime('%Y-%m-%d')
            cohort_costs = channel_costs[channel_costs["cohort"] == coh_row["cohort"]]
            row_data[col_header] = cohort_costs["costs"].sum()
        row_data["ВСЕГО"] = sum(row_data.values())
        table_data[channel] = row_data

    if not table_data:
        return pd.DataFrame()

    result = pd.DataFrame(table_data).T
    return _add_totals_row(result)


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
            str(unique_customers), period_start_str, period_end_str,
            str(num_orders), str(avg_orders_per_customer), str(max_orders_per_customer),
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
    return _build_sales_cohort_pivot(sales_df, cohorts_df, "Revenue")


def calculate_cost_table(sales_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate cost table by channel and cohort date range."""
    return _build_sales_cohort_pivot(sales_df, cohorts_df, "cost")


def calculate_promotion_costs_table(promotion_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate promotion costs table by channel and cohort."""
    return _build_expense_cohort_pivot(promotion_df, cohorts_df)


def calculate_other_marketing_costs_table(marketing_df: pd.DataFrame, cohorts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate other marketing costs table by channel and cohort."""
    return _build_expense_cohort_pivot(marketing_df, cohorts_df)


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
    return _build_sales_cohort_pivot(sales_df, cohorts_df, "Date", agg="count")


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


def _build_channel_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build a channel summary table with Сумма and Доля columns."""
    if df.empty or "ВСЕГО" not in df.columns:
        return pd.DataFrame()
    channels = [idx for idx in df.index if idx != "ИТОГО"]
    values = [df.loc[c, "ВСЕГО"] for c in channels]
    total = sum(values)
    rows = []
    for ch, v in zip(channels, values):
        share = round((v / total) * 100, 2) if total else 0
        rows.append({"Канал": ch, "Сумма": v, "Доля": f"{share}%"})
    rows.append({"Канал": "ИТОГО", "Сумма": total, "Доля": "100%"})
    return pd.DataFrame(rows)


def calculate_profit_by_channel_table(profit_table: pd.DataFrame) -> pd.DataFrame:
    """Calculate profit by channel with share percentage."""
    return _build_channel_summary(profit_table)


def calculate_orders_by_channel_table(orders_table: pd.DataFrame) -> pd.DataFrame:
    """Calculate number of orders by channel with sum and share percentage."""
    return _build_channel_summary(orders_table)


def calculate_avg_profit_by_channel_table(profit_by_channel_df: pd.DataFrame, orders_by_channel_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate average profit per order by channel."""
    if profit_by_channel_df.empty or orders_by_channel_df.empty:
        return pd.DataFrame()
    
    profit_by_channel_df = profit_by_channel_df.copy()
    orders_by_channel_df = orders_by_channel_df.copy()
    
    if "Канал" in profit_by_channel_df.columns:
        profit_by_channel_df = profit_by_channel_df.set_index("Канал")
    if "Канал" in orders_by_channel_df.columns:
        orders_by_channel_df = orders_by_channel_df.set_index("Канал")
    
    channels = []
    avg_profits = []
    
    for channel in profit_by_channel_df.index:
        if channel == "ИТОГО":
            continue
        profit_val = profit_by_channel_df.loc[channel, "Сумма"] if "Сумма" in profit_by_channel_df.columns else 0
        orders_val = orders_by_channel_df.loc[channel, "Сумма"] if "Сумма" in orders_by_channel_df.columns else 0
        
        if orders_val != 0:
            avg_profit = profit_val / orders_val
        else:
            avg_profit = 0
        
        channels.append(channel)
        avg_profits.append(avg_profit)
    
    total_profit = profit_by_channel_df.loc["ИТОГО", "Сумма"] if "ИТОГО" in profit_by_channel_df.index and "Сумма" in profit_by_channel_df.columns else 0
    total_orders = orders_by_channel_df.loc["ИТОГО", "Сумма"] if "ИТОГО" in orders_by_channel_df.index and "Сумма" in orders_by_channel_df.columns else 0
    total_avg = total_profit / total_orders if total_orders != 0 else 0
    
    channels.append("ИТОГО")
    avg_profits.append(total_avg)
    
    return pd.DataFrame({"Канал": channels, "Сумма": avg_profits})


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