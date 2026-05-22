"""Common UI components for LTV Streamlit application."""
import io
from datetime import datetime

import pandas as pd
import streamlit as st

import cohorts
import data_loader
from sqlalchemy import text


def _save_segment_column(clients_df: pd.DataFrame, column: str) -> None:
    """Batch-save a segment column to the clients table (non-critical)."""
    try:
        if clients_df is None or clients_df.empty or column not in clients_df.columns:
            return
        engine = data_loader.get_engine()
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE clients ADD COLUMN IF NOT EXISTS {column} INTEGER"))
        seg_map = clients_df[["client_id", column]].dropna()
        seg_map[column] = seg_map[column].astype(int)
        seg_map.to_sql("_tmp_seg", engine, if_exists="replace", index=False)
        with engine.begin() as conn:
            conn.execute(text(f"""
                UPDATE clients c
                SET {column} = t.{column}
                FROM _tmp_seg t
                WHERE c.client_id = t.client_id
            """))
            conn.execute(text("DROP TABLE IF EXISTS _tmp_seg"))
    except Exception:
        pass  # Non-critical — segments computed in-memory for current session


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
            value=start_date,
            min_value=start_date,
            max_value=end_date,
            key="start_date_input"
        )
    with col_end:
        selected_end_date = st.date_input(
            "End Date",
            value=end_date,
            min_value=start_date,
            max_value=end_date,
            key="end_date_input"
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
            file_key = f"s_{uploaded_sales.name}_{uploaded_sales.size}"
            if st.session_state.get("upl_sales_key") != file_key:
                st.session_state.upl_sales_key = file_key
                st.session_state.upl_sales_ok = False
                try:
                    data_loader.load_custom_sales_to_db(uploaded_sales)
                    st.session_state.upl_sales_ok = True
                except Exception as e:
                    st.error(f"Ошибка: {e}")

            if st.session_state.get("upl_sales_ok", False):
                st.success("Данные о продажах загружены!")
        else:
            st.session_state.pop("upl_sales_key", None)
            st.session_state.pop("upl_sales_ok", None)

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
            file_key = f"p_{uploaded_promotion.name}_{uploaded_promotion.size}"
            if st.session_state.get("upl_promo_key") != file_key:
                st.session_state.upl_promo_key = file_key
                st.session_state.upl_promo_ok = False
                try:
                    data_loader.load_custom_promotion_costs_to_db(uploaded_promotion)
                    st.session_state.upl_promo_ok = True
                except Exception as e:
                    st.error(f"Ошибка: {e}")

            if st.session_state.get("upl_promo_ok", False):
                st.success("Расходы на привлечение загружены!")
        else:
            st.session_state.pop("upl_promo_key", None)
            st.session_state.pop("upl_promo_ok", None)

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
            file_key = f"m_{uploaded_marketing.name}_{uploaded_marketing.size}"
            if st.session_state.get("upl_mkt_key") != file_key:
                st.session_state.upl_mkt_key = file_key
                st.session_state.upl_mkt_ok = False
                try:
                    data_loader.load_custom_other_marketing_costs_to_db(uploaded_marketing)
                    st.session_state.upl_mkt_ok = True
                except Exception as e:
                    st.error(f"Ошибка: {e}")

            if st.session_state.get("upl_mkt_ok", False):
                st.success("Прочие маркетинговые расходы загружены!")
        else:
            st.session_state.pop("upl_mkt_key", None)
            st.session_state.pop("upl_mkt_ok", None)


def render_section(section: str, start_date: datetime, end_date: datetime, **kwargs) -> None:
    """Render appropriate section based on selection."""
    if section == "Загрузка данных":
        render_data_upload_section()
    elif section == "Общий анализ":
        from ui_general import render_overall_analysis
        render_overall_analysis(
            start_date, end_date,
            kwargs.get("cohort_dates", []),
            kwargs.get("num_cohorts", 8),
            kwargs.get("cohort_size", 3),
            kwargs.get("is_days", False)
        )
    elif section == "RFM анализ":
        from ui_rfm import render_rfm_analysis
        render_rfm_analysis(start_date, end_date)
    elif section == "Когортный анализ":
        from ui_cohort import render_cohort_analysis
        render_cohort_analysis(kwargs.get("cohort_dates", []))
