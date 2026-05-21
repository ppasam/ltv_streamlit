"""Общий анализ section for LTV Streamlit application."""
from datetime import datetime
from decimal import Decimal

import pandas as pd
import streamlit as st

import analysis
import cohorts
import data_loader
import plotting


def render_overall_analysis(
    selected_start_date: datetime,
    selected_end_date: datetime,
    cohort_dates: list,
    num_cohorts: int,
    cohort_size: int,
    is_days: bool
) -> None:
    """Render Общий анализ section."""
    st.header("Общий анализ")

    cohort_type = cohorts.COHORT_TYPE_MONTHS if not is_days else cohorts.COHORT_TYPE_DAYS
    calculation_mode = st.session_state.get("calculation_mode", "Cohort Size")

    params_key = (
        selected_start_date, selected_end_date, cohort_size,
        num_cohorts, calculation_mode, cohort_type
    )
    if st.session_state.get("_cohort_params") != params_key:
        st.session_state._cohort_params = params_key
        data_loader.update_cohorts_in_db(
            start_date=selected_start_date,
            end_date=selected_end_date,
            cohort_type=cohort_type,
            cohort_size=cohort_size,
            num_cohorts=num_cohorts,
            calculation_mode=calculation_mode
        )
        st.cache_data.clear()
        data_loader.populate_clients_from_sales()

    sales_df = data_loader.load_sales_from_db(
        datetime.combine(selected_start_date, datetime.min.time()),
        datetime.combine(selected_end_date, datetime.min.time())
    )
    clients_df = data_loader.load_clients_from_db()
    promotion_df = data_loader.load_promotion_costs_from_db()
    marketing_df = data_loader.load_other_marketing_costs_from_db()

    cohorts_df = data_loader.load_cohorts_from_db()
    if not cohorts_df.empty:
        cohorts_df["date_start"] = pd.to_datetime(cohorts_df["date_start"])
        cohorts_df["date_end"] = pd.to_datetime(cohorts_df["date_end"])
        cohorts_df = cohorts_df[
            (cohorts_df["date_start"] >= selected_start_date) &
            (cohorts_df["date_end"] <= selected_end_date)
        ]

    metrics_df = analysis.calculate_overall_metrics(sales_df, promotion_df, marketing_df, clients_df)
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    max_orders = int(clients_df["num_orders"].max()) if clients_df is not None and not clients_df.empty else int(sales_df.groupby("Customer ID").size().max()) if "Customer ID" in sales_df.columns and not sales_df.empty else 0
    st.session_state.max_orders_per_customer = max_orders

    if clients_df is not None and not clients_df.empty and "total_amount" in clients_df.columns:
        max_monetary = Decimal(str(round(float(clients_df["total_amount"].max()), 2)))
    elif "Customer ID" in sales_df.columns and "Revenue" in sales_df.columns and not sales_df.empty:
        max_monetary = Decimal(str(round(float(sales_df.groupby("Customer ID")["Revenue"].sum().max()), 2)))
    else:
        max_monetary = Decimal("0.02")
    st.session_state.max_monetary_per_customer = max_monetary

    revenue_table = analysis.calculate_revenue_table(sales_df, cohorts_df)
    cost_table = analysis.calculate_cost_table(sales_df, cohorts_df)
    promotion_costs_table = analysis.calculate_promotion_costs_table(promotion_df, cohorts_df)
    other_costs_table = analysis.calculate_other_marketing_costs_table(marketing_df, cohorts_df)
    profit_table = analysis.calculate_profit_table(revenue_table, cost_table, promotion_costs_table, other_costs_table)

    st.divider()

    st.subheader("Прибыль по каналам привлечения")
    profit_by_channel_table = analysis.calculate_profit_by_channel_table(profit_table)
    if not profit_by_channel_table.empty:
        formatted_channel = profit_by_channel_table.style.format({"Сумма": "{:,.2f}"})
        st.dataframe(formatted_channel, use_container_width=True, hide_index=True)
    else:
        st.warning("Нет данных")

    st.divider()

    fig_profit = plotting.create_profit_by_channel_pie_chart(profit_by_channel_table)
    if fig_profit:
        st.plotly_chart(fig_profit, use_container_width=True)

    st.divider()

    st.subheader("Количество заказов по каналам привлечения")
    orders_table = analysis.calculate_orders_table(sales_df, cohorts_df)
    orders_by_channel = analysis.calculate_orders_by_channel_table(orders_table)
    if not orders_by_channel.empty:
        formatted_orders_by_channel = orders_by_channel.style.format({"Сумма": "{:,.0f}"})
        st.dataframe(formatted_orders_by_channel, use_container_width=True, hide_index=True)
    else:
        st.warning("Нет данных")

    st.divider()

    fig_orders = plotting.create_orders_by_channel_pie_chart(orders_by_channel)
    if fig_orders:
        st.plotly_chart(fig_orders, use_container_width=True)

    st.divider()

    st.subheader("Средняя прибыль с заказа")
    avg_profit_by_channel = analysis.calculate_avg_profit_by_channel_table(profit_by_channel_table, orders_by_channel)
    if not avg_profit_by_channel.empty:
        formatted_avg_profit = avg_profit_by_channel.style.format({"Сумма": "{:,.2f}"})
        st.dataframe(formatted_avg_profit, use_container_width=True, hide_index=True)
    else:
        st.warning("Нет данных")

    st.divider()

    fig_avg_profit = plotting.create_avg_profit_bar_chart(avg_profit_by_channel)
    if fig_avg_profit:
        st.plotly_chart(fig_avg_profit, use_container_width=True)

    st.divider()

    st.subheader("Выручка")
    if not revenue_table.empty:
        formatted_revenue = revenue_table.style.format("{:,.2f}")
        st.dataframe(formatted_revenue, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Себестоимость продаж")
    if not cost_table.empty:
        formatted_cost = cost_table.style.format("{:,.2f}")
        st.dataframe(formatted_cost, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Расходы на привлечение и удержание")
    if not promotion_costs_table.empty:
        formatted_promotion = promotion_costs_table.style.format("{:,.2f}")
        st.dataframe(formatted_promotion, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Прочие затраты")
    if not other_costs_table.empty:
        formatted_other = other_costs_table.style.format("{:,.2f}")
        st.dataframe(formatted_other, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Прибыль")
    if not profit_table.empty:
        formatted_profit = profit_table.style.format("{:,.2f}")
        st.dataframe(formatted_profit, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    fig_profit_trend = plotting.create_profit_trend_chart(profit_table)
    if fig_profit_trend:
        st.plotly_chart(fig_profit_trend, use_container_width=True)

    st.divider()

    st.subheader("Количество заказов")
    if not orders_table.empty:
        formatted_orders = orders_table.style.format("{:,.0f}")
        st.dataframe(formatted_orders, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Средние затраты на привлечение заказа в квартал")
    avg_acquisition_table = analysis.calculate_avg_acquisition_cost_table(promotion_costs_table, orders_table)
    if not avg_acquisition_table.empty:
        formatted_avg_acquisition = avg_acquisition_table.style.format("{:,.2f}")
        st.dataframe(formatted_avg_acquisition, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Средняя прибыль с заказа")
    avg_profit_table = analysis.calculate_avg_profit_per_order_table(profit_table, orders_table)
    if not avg_profit_table.empty:
        formatted_avg_profit = avg_profit_table.style.format("{:,.2f}")
        st.dataframe(formatted_avg_profit, use_container_width=True)
    else:
        st.warning("Нет данных")
