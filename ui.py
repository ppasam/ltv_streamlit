"""UI module for LTV Streamlit application."""
import io
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

import analysis
import cohorts
import data_loader
import plotting


def render_sidebar(start_date: datetime, end_date: datetime) -> tuple:
    """Render sidebar with settings and return selected values."""
    st.sidebar.header("Navigation")
    section = st.sidebar.radio(
        "Select Section",
        ["Общий анализ", "RFM анализ", "Когортный анализ", "Загрузка данных"]
    )

    st.sidebar.header("Date Range")
    col_start, col_end = st.sidebar.columns(2)
    with col_start:
        selected_start_date = st.date_input(
            "Start Date",
            value=start_date.date(),
            min_value=start_date.date(),
            max_value=end_date.date()
        )
    with col_end:
        selected_end_date = st.date_input(
            "End Date",
            value=end_date.date(),
            min_value=start_date.date(),
            max_value=end_date.date()
        )

    selected_start = datetime.combine(selected_start_date, datetime.min.time())
    selected_end = datetime.combine(selected_end_date, datetime.min.time())

    cohort_type, num_cohorts, cohort_size, cohort_dates, is_days = cohorts.render_cohort_settings(
        selected_start, selected_end, st.session_state.get("calculation_mode", "Cohort Size")
    )

    return section, selected_start, selected_end, cohort_type, num_cohorts, cohort_size, cohort_dates, is_days


def render_data_upload_section() -> None:
    """Render data upload section."""
    st.header("Загрузка данных")

    data_sources = data_loader.get_current_data_source()

    sales_status = "✅ Шаблон по умолчанию" if data_sources["sales"] == "default" else "📁 Кастомные данные"
    promotion_status = "✅ Шаблон по умолчанию" if data_sources["promotion_costs"] == "default" else "📁 Кастомные данные"

    st.subheader("1. Данные о продажах")
    st.markdown(f"**Статус:** {sales_status}")
    st.markdown("""
    **Поля данных:**
    - `purchase_date` — Дата покупки (YYYY-MM-DD)
    - `order_id` — ID заказа
    - `order_price` — Стоимость заказа
    - `cost` — Себестоимость
    - `client_id` — ID клиента
    - `acquisition_channel` — Канал привлечения
    """)
    col_dl1, col_load1 = st.columns([1, 1])

    sales_df = data_loader.load_sales_data()
    buffer = io.BytesIO()
    sales_df.to_excel(buffer, index=False, engine="openpyxl")
    with col_dl1:
        st.download_button(
            "📤 Скачать шаблон",
            data=buffer.getvalue(),
            file_name="sales_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_sales",
            use_container_width=True
        )
    with col_load1:
        uploaded_sales = st.file_uploader("📥 Загрузить свои данные", type=["xlsx"], key="upload_sales", label_visibility="collapsed")
        if uploaded_sales:
            try:
                data_loader.load_custom_sales_to_db(uploaded_sales)
                st.success("Данные о продажах загружены!")
            except Exception as e:
                st.error(f"Ошибка: {e}")

    st.divider()

    st.subheader("2. Расходы на привлечение и удержание клиентов")
    st.markdown("""
    **Поля данных:**
    - `channels` — Название канала (например, Яндекс.Директ, Google Ads)
    - `expenses_date` — Дата окончания периода (YYYY-MM-DD)
    - `costs` — Сумма расходов
    """)
    col_dl2, col_load2 = st.columns([1, 1])

    promotion_df = data_loader.load_promotion_costs_data()
    buffer = io.BytesIO()
    promotion_df.to_excel(buffer, index=False, engine="openpyxl")
    with col_dl2:
        st.download_button(
            "📤 Скачать шаблон",
            data=buffer.getvalue(),
            file_name="promotion_costs_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_promotion",
            use_container_width=True
        )
    with col_load2:
        uploaded_promotion = st.file_uploader("📥 Загрузить свои данные", type=["xlsx"], key="upload_promotion", label_visibility="collapsed")
        if uploaded_promotion:
            try:
                data_loader.load_custom_promotion_costs_to_db(uploaded_promotion)
                st.success("Расходы на привлечение загружены!")
            except Exception as e:
                st.error(f"Ошибка: {e}")

    st.divider()

    st.subheader("3. Прочие маркетинговые расходы")
    st.markdown("""
    **Поля данных:**
    - `channels` — Название канала (например, Email, SMM)
    - `expenses_date` — Дата окончания периода (YYYY-MM-DD)
    - `costs` — Сумма расходов
    """)
    col_dl3, col_load3 = st.columns([1, 1])

    marketing_df = data_loader.load_other_marketing_costs_data()
    buffer = io.BytesIO()
    marketing_df.to_excel(buffer, index=False, engine="openpyxl")
    with col_dl3:
        st.download_button(
            "📤 Скачать шаблон",
            data=buffer.getvalue(),
            file_name="other_marketing_costs_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_marketing",
            use_container_width=True
        )
    with col_load3:
        uploaded_marketing = st.file_uploader("📥 Загрузить свои данные", type=["xlsx"], key="upload_marketing", label_visibility="collapsed")
        if uploaded_marketing:
            try:
                data_loader.load_custom_other_marketing_costs_to_db(uploaded_marketing)
                st.success("Прочие маркетинговые расходы загружены!")
            except Exception as e:
                st.error(f"Ошибка: {e}")


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

    sales_df = data_loader.load_sales_from_db(
        datetime.combine(selected_start_date, datetime.min.time()),
        datetime.combine(selected_end_date, datetime.min.time())
    )
    data_loader.populate_clients_from_sales()
    clients_df = data_loader.load_clients_from_db()
    promotion_df = data_loader.load_promotion_costs_from_db()
    marketing_df = data_loader.load_other_marketing_costs_from_db()
    cohorts_df = data_loader.load_cohorts_from_db()

    metrics_df = analysis.calculate_overall_metrics(sales_df, promotion_df, marketing_df, clients_df)
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Выручка")
    revenue_table = analysis.calculate_revenue_table(sales_df, cohorts_df)
    if not revenue_table.empty:
        formatted_revenue = revenue_table.style.format("{:,.2f}")
        st.dataframe(formatted_revenue, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Себестоимость продаж")
    cost_table = analysis.calculate_cost_table(sales_df, cohorts_df)
    if not cost_table.empty:
        formatted_cost = cost_table.style.format("{:,.2f}")
        st.dataframe(formatted_cost, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Расходы на привлечение и удержание")
    promotion_costs_table = analysis.calculate_promotion_costs_table(promotion_df, cohorts_df)
    if not promotion_costs_table.empty:
        formatted_promotion = promotion_costs_table.style.format("{:,.2f}")
        st.dataframe(formatted_promotion, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Прочие затраты")
    other_costs_table = analysis.calculate_other_marketing_costs_table(marketing_df, cohorts_df)
    if not other_costs_table.empty:
        formatted_other = other_costs_table.style.format("{:,.2f}")
        st.dataframe(formatted_other, use_container_width=True)
    else:
        st.warning("Нет данных")

    st.divider()

    st.subheader("Прибыль")
    profit_table = analysis.calculate_profit_table(revenue_table, cost_table, promotion_costs_table, other_costs_table)
    if not profit_table.empty:
        formatted_profit = profit_table.style.format("{:,.2f}")
        st.dataframe(formatted_profit, use_container_width=True)
    else:
        st.warning("Нет данных")


def render_rfm_analysis() -> None:
    """Render RFM анализ section."""
    st.header("RFM анализ")
    st.info("🚧 В разработке")


def render_cohort_analysis() -> None:
    """Render Когортный анализ section."""
    st.header("Когортный анализ")
    st.info("🚧 В разработке")


def render_section(section: str, start_date: datetime, end_date: datetime, **kwargs) -> None:
    """Render appropriate section based on selection."""
    if section == "Загрузка данных":
        render_data_upload_section()
    elif section == "Общий анализ":
        render_overall_analysis(
            start_date, end_date,
            kwargs.get("cohort_dates", []),
            kwargs.get("num_cohorts", 8),
            kwargs.get("cohort_size", 3),
            kwargs.get("is_days", False)
        )
    elif section == "RFM анализ":
        render_rfm_analysis()
    elif section == "Когортный анализ":
        render_cohort_analysis()