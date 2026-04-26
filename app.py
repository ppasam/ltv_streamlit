"""Main Streamlit application for LTV analysis."""
import io
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st

import analysis
import cohorts
import data_loader
import plotting


st.set_page_config(page_title="LTV", layout="wide")

st.title("LTV")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ltv_user:ltv_pass@localhost:5432/ltv_db"
)

if "initialized" not in st.session_state:
    st.session_state.initialized = False
    data_loader.init_database_from_templates()
    st.session_state.initialized = True
if "cohort_size_input" not in st.session_state:
    st.session_state.cohort_size_input = 3
if "num_cohorts_input" not in st.session_state:
    st.session_state.num_cohorts_input = 8
if "cohort_dates_input" not in st.session_state:
    st.session_state.cohort_dates_input = []
if "prev_cohort_size" not in st.session_state:
    st.session_state.prev_cohort_size = 3
if "prev_num_cohorts" not in st.session_state:
    st.session_state.prev_num_cohorts = 8


def initialize_data() -> None:
    """Initialize database with data from Excel files."""
    try:
        data_loader.init_database()
        st.session_state.initialized = True
        st.success("Data loaded successfully!")
    except Exception as e:
        st.error(f"Error loading data: {e}")


def get_date_range() -> tuple[datetime, datetime]:
    """Get date range from sales data."""
    try:
        return data_loader.get_sales_date_range()
    except Exception:
        return datetime(2013, 1, 1), datetime(2014, 12, 31)


def main() -> None:
    """Main application function."""
    start_date, end_date = get_date_range()

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

    st.sidebar.header("Cohort Settings")
    cohort_type = st.sidebar.selectbox(
        "Type of Cohort Size",
        [cohorts.COHORT_TYPE_MONTHS, cohorts.COHORT_TYPE_DAYS],
        index=0
    )

    if "calculation_mode" not in st.session_state:
        st.session_state.calculation_mode = "Cohort Size"

    calculation_mode = st.sidebar.radio(
        "База расчета",
        ["Количество дней/месяцев в когорте", "Количество когорт"],
        index=0 if st.session_state.calculation_mode == "Cohort Size" else 1
    )
    st.session_state.calculation_mode = "Cohort Size" if calculation_mode == "Количество дней/месяцев в когорте" else "Number of Cohorts"

    max_cohort_size = 365 if cohort_type == cohorts.COHORT_TYPE_DAYS else 24

    if st.session_state.calculation_mode == "Cohort Size":
        label_size = f"Количество {'дней' if cohort_type == cohorts.COHORT_TYPE_DAYS else 'месяцев'} в когорте"
        cohort_size_input = st.sidebar.number_input(
            label_size,
            min_value=1,
            max_value=max_cohort_size,
            value=st.session_state.cohort_size_input,
            key="cohort_size_widget"
        )

        if cohort_size_input != st.session_state.cohort_size_input:
            num_cohorts_new, cohort_dates = cohorts.recalculate_from_cohort_size(
                start_date=datetime.combine(selected_start_date, datetime.min.time()),
                end_date=datetime.combine(selected_end_date, datetime.min.time()),
                cohort_type=cohort_type,
                cohort_size=cohort_size_input
            )
            st.session_state.cohort_size_input = cohort_size_input
            st.session_state.num_cohorts_input = num_cohorts_new
            st.session_state._needs_rerun = True
        else:
            num_cohorts_new = st.session_state.num_cohorts_input

        st.sidebar.info(f"📊 Рассчитанное количество когорт: **{num_cohorts_new}**")
    else:
        num_cohorts_input = st.sidebar.number_input(
            "Количество когорт",
            min_value=1,
            max_value=cohorts.MAX_COHORTS,
            value=st.session_state.num_cohorts_input,
            key="num_cohorts_widget"
        )

        if num_cohorts_input != st.session_state.num_cohorts_input:
            cohort_size_new, cohort_dates_new = cohorts.recalculate_from_num_cohorts(
                start_date=datetime.combine(selected_start_date, datetime.min.time()),
                end_date=datetime.combine(selected_end_date, datetime.min.time()),
                cohort_type=cohort_type,
                num_cohorts=num_cohorts_input
            )
            st.session_state.cohort_size_input = cohort_size_new
            st.session_state.num_cohorts_input = num_cohorts_input
            st.session_state._temp_cohort_dates = cohort_dates_new
            st.session_state._needs_rerun = True
        else:
            cohort_size_new = st.session_state.cohort_size_input
            cohort_dates_new = st.session_state.get("_temp_cohort_dates", [])

        st.sidebar.info(f"📊 Количество {'дней' if cohort_type == cohorts.COHORT_TYPE_DAYS else 'месяцев'} в когорте: **{cohort_size_new}**")
        st.session_state._temp_cohort_dates = cohort_dates_new

    st.session_state.prev_cohort_size = st.session_state.cohort_size_input
    st.session_state.prev_num_cohorts = st.session_state.num_cohorts_input

    cohort_size = st.session_state.cohort_size_input
    num_cohorts = st.session_state.num_cohorts_input

    if st.session_state.calculation_mode == "Cohort Size":
        _, cohort_dates = cohorts.recalculate_from_cohort_size(
            start_date=datetime.combine(selected_start_date, datetime.min.time()),
            end_date=datetime.combine(selected_end_date, datetime.min.time()),
            cohort_type=cohort_type,
            cohort_size=cohort_size
        )
    else:
        cached_dates = st.session_state.get("_temp_cohort_dates", [])
        if cached_dates:
            cohort_dates = cached_dates
        else:
            _, cohort_dates = cohorts.recalculate_from_num_cohorts(
                start_date=datetime.combine(selected_start_date, datetime.min.time()),
                end_date=datetime.combine(selected_end_date, datetime.min.time()),
                cohort_type=cohort_type,
                num_cohorts=num_cohorts
            )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Cohort Start Dates")
    edited_dates = []
    for i in range(len(cohort_dates)):
        default_val = cohort_dates[i].strftime('%Y-%m-%d')
        new_date = st.sidebar.text_input(
            f"Cohort {i+1}", 
            value=default_val, 
            key=f"cohort_date_{i}_{id(cohort_dates)}"
        )
        try:
            edited_dates.append(datetime.strptime(new_date, '%Y-%m-%d'))
        except:
            edited_dates.append(cohort_dates[i])
    st.session_state.cohort_dates_input = edited_dates

    if st.session_state.get("_needs_rerun", False):
        st.session_state._needs_rerun = False
        st.rerun()

    if section == "Загрузка данных":
        st.header("Загрузка данных")

        data_sources = data_loader.get_current_data_source()

        sales_status = "✅ Шаблон по умолчанию" if data_sources["sales"] == "default" else "📁 Кастомные данные"
        promotion_status = "✅ Шаблон по умолчанию" if data_sources["promotion_costs"] == "default" else "📁 Кастомные данные"
        marketing_status = "✅ Шаблон по умолчанию" if data_sources["other_marketing_costs"] == "default" else "📁 Кастомные данные"

        st.info(f"""
        **Текущие данные в PostgreSQL:**

        • Данные о продажах: {sales_status}
        • Расходы на привлечение: {promotion_status}
        • Прочие маркетинговые расходы: {marketing_status}
        """)

        st.subheader("1. Данные о продажах")
        st.markdown("""
        **Поля данных:**
        - `purchase_date` — Дата покупки (YYYY-MM-DD)
        - `order_id` — Уникальный идентификатор заказа
        - `order_price` — Стоимость заказа
        - `cost` — Себестоимость заказа
        - `client_id` — Идентификатор клиента
        - `acquisition_channel` — Канал привлечения клиента
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
        - `period_end` — Дата окончания периода (YYYY-MM-DD)
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
        - `period_end` — Дата окончания периода (YYYY-MM-DD)
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

    elif section == "Общий анализ":
        st.header("Общий анализ")

        start_date, end_date = get_date_range()

        if not st.session_state.cohort_dates_input:
            _, cohort_dates = cohorts.recalculate_from_num_cohorts(
                start_date=datetime.combine(selected_start_date, datetime.min.time()),
                end_date=datetime.combine(selected_end_date, datetime.min.time()),
                cohort_type=cohorts.COHORT_TYPE_MONTHS,
                num_cohorts=st.session_state.num_cohorts_input
            )
        else:
            cohort_dates = st.session_state.cohort_dates_input

        num_cohorts = len(cohort_dates) if cohort_dates else 8
        cohort_type = st.session_state.get("calculation_mode", "Cohort Size")
        cohort_size = st.session_state.cohort_size_input
        is_days = cohort_type != "Cohort Size" or st.session_state.get("_cohort_type_days", False)

        st.subheader("Общие показатели")
        sales_df = data_loader.load_sales_from_db(
            datetime.combine(selected_start_date, datetime.min.time()),
            datetime.combine(selected_end_date, datetime.min.time())
        )
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

        promotion_df = data_loader.load_promotion_costs_from_db()
        acquisition_costs_val = promotion_df["costs"].sum() if not promotion_df.empty and "costs" in promotion_df.columns else 0
        acquisition_costs = f"${acquisition_costs_val:,.2f}"

        marketing_df = data_loader.load_other_marketing_costs_from_db()
        other_costs_val = marketing_df["costs"].sum() if not marketing_df.empty and "costs" in marketing_df.columns else 0
        other_costs = f"${other_costs_val:,.2f}"

        profit_val = total_revenue - total_cost - acquisition_costs_val - other_costs_val
        profit = f"${profit_val:,.2f}"
        margin = f"{(profit_val / total_revenue * 100):.2f}%" if total_revenue > 0 else "0.00%"

        metrics_data = {
            "Показатель": ["Количество уникальных клиентов", "Начало периода", "Конец периода", "Количество заказов", "В среднем заказов на 1 клиента", "Максимально заказов на 1 клиента", "Средняя цена заказа", "Минимальная цена заказа", "Максимальная цена заказа", "Минимальная сумма заказов на 1 клиента", "Максимальная сумма заказов на 1 клиента", "Выручка", "Себестоимость продаж", "Средняя наценка", "Валовая прибыль", "Валовая маржа", "Затраты на привлечение клиентов", "Прочие затраты", "Прибыль", "Маржа"],
            "Значение": [unique_customers, period_start_str, period_end_str, num_orders, avg_orders_per_customer, max_orders_per_customer, avg_order_price, min_order_price, max_order_price, min_revenue_per_customer, max_revenue_per_customer, total_revenue_str, total_cost_str, avg_margin, gross_profit, gross_margin, acquisition_costs, other_costs, profit, margin]
        }
        metrics_df = pd.DataFrame(metrics_data)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("1. Расходы на привлечение и удержание")
        promotion_df = data_loader.load_promotion_costs_from_db()

        if not promotion_df.empty:
            if "period_end" in promotion_df.columns and "channels" in promotion_df.columns and "costs" in promotion_df.columns:
                promotion_df["period_end"] = pd.to_datetime(promotion_df["period_end"])

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
                table_data = {}

                for channel in promotion_df["channels"].unique():
                    table_data[channel] = [0] * num_cohorts

                for _, row in promotion_df.iterrows():
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

                formatted_table = table_df.style.format("${:,.2f}")
                st.dataframe(formatted_table, use_container_width=True)
            else:
                st.warning("Неверный формат данных")
        else:
            st.warning("Нет данных")

        st.divider()

        st.subheader("2. Прочие затраты")
        marketing_df = data_loader.load_other_marketing_costs_from_db()

        if not marketing_df.empty:
            if "period_end" in marketing_df.columns and "channels" in marketing_df.columns and "costs" in marketing_df.columns:
                marketing_df["period_end"] = pd.to_datetime(marketing_df["period_end"])

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
                table_data = {}

                for channel in marketing_df["channels"].unique():
                    table_data[channel] = [0] * num_cohorts

                for _, row in marketing_df.iterrows():
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

                formatted_table = table_df.style.format("${:,.2f}")
                st.dataframe(formatted_table, use_container_width=True)
            else:
                st.warning("Неверный формат данных")
        else:
            st.warning("Нет данных")

    elif section == "RFM анализ":
        st.header("RFM анализ")
        st.info("🚧 В разработке")

    elif section == "Когортный анализ":
        st.header("Когортный анализ")
        st.info("🚧 В разработке")


if __name__ == "__main__":
    main()