"""UI module for LTV Streamlit application."""
import io
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
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
            max_value=end_date.date(),
            key="start_date_input"
        )
    with col_end:
        selected_end_date = st.date_input(
            "End Date",
            value=end_date.date(),
            min_value=start_date.date(),
            max_value=end_date.date(),
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

    cohort_type = cohorts.COHORT_TYPE_MONTHS if not is_days else cohorts.COHORT_TYPE_DAYS
    calculation_mode = st.session_state.get("calculation_mode", "Cohort Size")
    data_loader.update_cohorts_in_db(
        start_date=selected_start_date,
        end_date=selected_end_date,
        cohort_type=cohort_type,
        cohort_size=cohort_size,
        num_cohorts=num_cohorts,
        calculation_mode=calculation_mode
    )

    st.cache_data.clear()

    sales_df = data_loader.load_sales_from_db(
        datetime.combine(selected_start_date, datetime.min.time()),
        datetime.combine(selected_end_date, datetime.min.time())
    )
    data_loader.populate_clients_from_sales()
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


def create_financial_counter(
    label: str,
    key: str,
    min_value: Decimal,
    max_value: Decimal,
    step: Decimal,
    default_value: Decimal
) -> Decimal:
    """
    Компонент-счетчик финансовых данных для Streamlit.
    
    Параметры:
        label: Название счетчика
        key: Уникальный ключ для session_state
        min_value: Минимальное значение (включительно)
        max_value: Максимальное значение (включительно)
        step: Шаг изменения значения
        default_value: Значение по умолчанию
    
    Возвращает:
        Текущее значение типа Decimal
    """
    # Константы для валидации
    MIN_VALUE = min_value
    MAX_VALUE = max_value
    STEP = step
    
    # Инициализация в session_state
    session_key = f"counter_{key}"
    if session_key not in st.session_state:
        # Проверяем, что default_value в пределах диапазона
        if default_value < MIN_VALUE:
            st.session_state[session_key] = MIN_VALUE
        elif default_value > MAX_VALUE:
            st.session_state[session_key] = MAX_VALUE
        else:
            st.session_state[session_key] = default_value
    
    # Получаем текущее значение из session_state
    current_value = Decimal(str(st.session_state[session_key]))
    
    # Форматируем значение для отображения (X.XX)
    display_value = current_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Вычисляем следующие значения для определения активности кнопок
    next_minus = (current_value - STEP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    next_plus = (current_value + STEP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Кнопка "минус" неактивна если следующее значение меньше минимума
    minus_disabled = next_minus < MIN_VALUE
    
    # Кнопка "плюс" неактивна если следующее значение больше максимума
    plus_disabled = next_plus > MAX_VALUE
    
    # UI: три колонки [минус] [значение] [плюс]
    col_minus, col_value, col_plus = st.columns([1, 2, 1])
    
    with col_minus:
        if st.button("−", key=f"{key}_minus", help="Уменьшить", disabled=minus_disabled):
            new_value = (current_value - STEP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            st.session_state[session_key] = new_value
            st.rerun()
    
    with col_value:
        st.write(f"{label}")
        st.write(f"**{display_value}**")
    
    with col_plus:
        if st.button("+", key=f"{key}_plus", help="Увеличить", disabled=plus_disabled):
            new_value = (current_value + STEP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            st.session_state[session_key] = new_value
            st.rerun()
    
    return current_value


def render_rfm_analysis(start_date: datetime, end_date: datetime) -> None:
    """Render RFM анализ section."""
    st.header("RFM анализ")

    max_r = (end_date - start_date).days
    if max_r < 2:
        max_r = 2

    if "rfm_values_r" not in st.session_state:
        st.session_state.rfm_values_r = [30, 90, 365]
    if "rfm_key_r" not in st.session_state:
        st.session_state.rfm_key_r = 0

    max_r2 = max_r
    max_r3 = max_r
    max_r4 = max_r
    if max_r2 < 30:
        max_r2 = 30
        max_r3 = 90
        max_r4 = max_r

    vals_r = st.session_state.rfm_values_r
    key_r = st.session_state.rfm_key_r

    st.subheader("Задаем количество дней для периодов сегментов R - Recency")

    c1, c2, c3 = st.columns(3)
    with c1:
        r2 = st.number_input("для сегмента 2", min_value=2, max_value=max_r2, value=min(vals_r[0], max_r2), key=f"r2_{key_r}")
    with c2:
        r3 = st.number_input("для сегмента 3", min_value=2, max_value=max_r3, value=min(vals_r[1], max_r3), key=f"r3_{key_r}")
    with c3:
        r4 = st.number_input("для сегмента 4", min_value=2, max_value=max_r4, value=min(vals_r[2], max_r4), key=f"r4_{key_r}")

    r2_n, r3_n, r4_n = r2, r3, r4

    if r2_n >= r3_n:
        r3_n = r2_n + 1
    if r3_n >= r4_n:
        r4_n = r3_n + 1
    if r4_n > max_r4:
        r4_n = max_r4
    if r3_n > max_r3:
        r3_n = max_r3
    if r2_n > max_r2:
        r2_n = max_r2

    if r2_n != vals_r[0] or r3_n != vals_r[1] or r4_n != vals_r[2]:
        st.session_state.rfm_values_r = [r2_n, r3_n, r4_n]
        st.session_state.rfm_key_r = key_r + 1
        st.rerun()

    recency_data = [
        {"с": 0, "по": r2_n - 1, "№ сегмента R": 1},
        {"с": r2_n, "по": r3_n - 1, "№ сегмента R": 2},
        {"с": r3_n, "по": r4_n - 1, "№ сегмента R": 3},
        {"с": r4_n, "по": max_r, "№ сегмента R": 4},
    ]
    st.subheader("Кол-во клиентов, сделавших последнюю покупку в период \"с - по\" дней назад (Recency)")
    st.dataframe(recency_data, use_container_width=True, hide_index=True)

    st.divider()

    if "rfm_values_f" not in st.session_state:
        st.session_state.rfm_values_f = [2, 3, 5]
    if "rfm_key_f" not in st.session_state:
        st.session_state.rfm_key_f = 0

    max_orders = st.session_state.get("max_orders_per_customer", 37)
    if max_orders < 2:
        max_orders = 37

    max_f2 = max_orders - 2
    max_f3 = max_orders - 1
    max_f4 = max_orders
    if max_f2 < 2:
        max_f2 = 2
        max_f3 = 3
        max_f4 = 4

    vals_f = st.session_state.rfm_values_f
    key_f = st.session_state.rfm_key_f

    st.subheader("Задаем количество покупок для сегментов F - Frequency")

    c1, c2, c3 = st.columns(3)
    with c1:
        f2 = st.number_input("для сегмента 2", min_value=2, max_value=max_f2, value=min(vals_f[0], max_f2), key=f"f2_{key_f}")
    with c2:
        f3 = st.number_input("для сегмента 3", min_value=2, max_value=max_f3, value=min(vals_f[1], max_f3), key=f"f3_{key_f}")
    with c3:
        f4 = st.number_input("для сегмента 4", min_value=2, max_value=max_f4, value=min(vals_f[2], max_f4), key=f"f4_{key_f}")

    f2_n, f3_n, f4_n = f2, f3, f4

    if f2_n >= f3_n:
        f3_n = f2_n + 1
    if f3_n >= f4_n:
        f4_n = f3_n + 1
    if f4_n > max_f4:
        f4_n = max_f4
    if f3_n > max_f3:
        f3_n = max_f3
    if f2_n > max_f2:
        f2_n = max_f2

    if f2_n != vals_f[0] or f3_n != vals_f[1] or f4_n != vals_f[2]:
        st.session_state.rfm_values_f = [f2_n, f3_n, f4_n]
        st.session_state.rfm_key_f = key_f + 1
        st.rerun()

    frequency_data = [
        {"min n": 1, "max n": f2_n - 1, "№ сегмента F": 4},
        {"min n": f2_n, "max n": f3_n - 1, "№ сегмента F": 3},
        {"min n": f3_n, "max n": f4_n - 1, "№ сегмента F": 2},
        {"min n": f4_n, "max n": max_orders, "№ сегмента F": 1},
    ]
    st.subheader("Кол-во клиентов, сделавших n покупок (Frequency)")
    st.dataframe(frequency_data, use_container_width=True, hide_index=True)

    st.subheader("Задаем суммы покупок для сегментов M - Monetary")

    # Параметры счетчиков (только Decimal)
    COUNTER_MIN = Decimal("0.02")
    COUNTER_STEP = Decimal("0.01")
    MIN_DIFF = COUNTER_STEP

    # Получаем max_monetary из "Общий анализ"
    max_monetary = st.session_state.get("max_monetary_per_customer", Decimal("0.02"))
    max_monetary = Decimal(str(max_monetary))

    # Инициализация session_state если отсутствует
    if "monetary_values_m" not in st.session_state:
        if max_monetary > Decimal("25000.00"):
            st.session_state.monetary_values_m = [Decimal("3000.00"), Decimal("10000.00"), Decimal("25000.00")]
        else:
            st.session_state.monetary_values_m = [max_monetary - Decimal("0.02"), max_monetary - Decimal("0.01"), max_monetary]

    vals_m = list(st.session_state.monetary_values_m)

    min_m2 = Decimal("0.019")
    min_m3 = Decimal("0.029")
    min_m4 = Decimal("0.039")
    if vals_m[0] < min_m2:
        vals_m[0] = min_m2
    if vals_m[1] < min_m3:
        vals_m[1] = min_m3
    if vals_m[2] < min_m4:
        vals_m[2] = min_m4
    st.session_state.monetary_values_m = vals_m

    # Для отслеживания изменений храним предыдущие значения
    prev_vals = st.session_state.get("monetary_prev_values_m", None)

    # Определяем какой счетчик изменился
    changed_idx = -1
    if prev_vals is not None:
        for i in range(3):
            if vals_m[i] != prev_vals[i]:
                changed_idx = i
                break

    # Если есть изменение - применяем правила распространения
    if changed_idx >= 0:
        new_vals = list(vals_m)
        if new_vals[changed_idx] > prev_vals[changed_idx]:
            for i in range(changed_idx, 2):
                required = new_vals[i] + MIN_DIFF
                if new_vals[i + 1] < required:
                    new_vals[i + 1] = required
        else:
            for i in range(changed_idx, 0, -1):
                required = new_vals[i] - MIN_DIFF
                if new_vals[i - 1] > required:
                    new_vals[i - 1] = required

        # Также корректируем вверх для max_monetary
        new_vals[2] = min(new_vals[2], max_monetary)
        new_vals[1] = min(new_vals[1], new_vals[2] - MIN_DIFF)
        new_vals[0] = min(new_vals[0], new_vals[1] - MIN_DIFF)

        if new_vals != vals_m:
            vals_m = new_vals
            st.session_state.monetary_values_m = vals_m
            st.session_state.monetary_prev_values_m = list(vals_m)
            st.rerun()

    # Сохраняем текущие значения для следующего рендера
    st.session_state.monetary_prev_values_m = list(vals_m)

    # Конвертируем Decimal в float для number_input (только для отображения)
    # Для каждого сегмента свое min и max
    min_float_m2 = float(Decimal("0.019"))
    min_float_m3 = float(Decimal("0.029"))
    min_float_m4 = float(Decimal("0.039"))
    max_float_m2 = max(min_float_m2, float(max_monetary - Decimal("0.02")))  # a - 0.02, but >= min
    max_float_m3 = max(min_float_m3, float(max_monetary - Decimal("0.01")))  # a - 0.01, but >= min
    max_float_m4 = max(min_float_m4, float(max_monetary))  # a, but >= min
    step_float = float(COUNTER_STEP)

    # Ключ для обновления number_input после rerun
    monetary_key_m = st.session_state.get("monetary_key_m", 0)

    c1, c2, c3 = st.columns(3)
    with c1:
        m2_raw = st.number_input("для сегмента 2", min_value=min_float_m2, max_value=max_float_m2, value=float(vals_m[0]), step=step_float, key=f"monetary_m2_{monetary_key_m}")
        m2_d = Decimal(str(m2_raw)).quantize(COUNTER_STEP, rounding=ROUND_HALF_UP)
        if m2_d != vals_m[0]:
            vals_m[0] = m2_d
            st.session_state.monetary_values_m = vals_m
            st.session_state.monetary_key_m = monetary_key_m + 1
            st.rerun()
    with c2:
        m3_raw = st.number_input("для сегмента 3", min_value=min_float_m3, max_value=max_float_m3, value=float(vals_m[1]), step=step_float, key=f"monetary_m3_{monetary_key_m}")
        m3_d = Decimal(str(m3_raw)).quantize(COUNTER_STEP, rounding=ROUND_HALF_UP)
        if m3_d != vals_m[1]:
            vals_m[1] = m3_d
            st.session_state.monetary_values_m = vals_m
            st.session_state.monetary_key_m = monetary_key_m + 1
            st.rerun()
    with c3:
        m4_raw = st.number_input("для сегмента 4", min_value=min_float_m4, max_value=max_float_m4, value=float(vals_m[2]), step=step_float, key=f"monetary_m4_{monetary_key_m}")
        m4_d = Decimal(str(m4_raw)).quantize(COUNTER_STEP, rounding=ROUND_HALF_UP)
        if m4_d != vals_m[2]:
            vals_m[2] = m4_d
            st.session_state.monetary_values_m = vals_m
            st.session_state.monetary_key_m = monetary_key_m + 1
            st.rerun()

    # Сохраняем точные Decimal значения
    st.session_state.monetary_values_m = [m2_d, m3_d, m4_d]

    # Таблица диапазонов Monetary
    st.subheader("Кол-во клиентов, сделавших покупок на сумму \"с - по\" (Monetary)")
    table_data = [
        {"с": Decimal("0.01"), "по": m2_d - COUNTER_STEP, "№ сегмента M": 4},
        {"с": m2_d, "по": m3_d - COUNTER_STEP, "№ сегмента M": 3},
        {"с": m3_d, "по": m4_d - COUNTER_STEP, "№ сегмента M": 2},
        {"с": m4_d, "по": max_monetary, "№ сегмента M": 1},
    ]
    st.table({"с": [str(row["с"].quantize(COUNTER_STEP)) for row in table_data],
              "по": [str(row["по"].quantize(COUNTER_STEP)) for row in table_data],
              "№ сегмента M": [row["№ сегмента M"] for row in table_data]})


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
        render_rfm_analysis(start_date, end_date)
    elif section == "Когортный анализ":
        render_cohort_analysis()