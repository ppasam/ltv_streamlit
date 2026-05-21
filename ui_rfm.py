"""RFM анализ section for LTV Streamlit application."""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import streamlit as st

import data_loader

from ui_common import _save_segment_column


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

    st.divider()

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

    clients_df = data_loader.load_clients_from_db()
    recency_counts = [0, 0, 0, 0]
    if clients_df is not None and not clients_df.empty and "last_order_date" in clients_df.columns:
        clients_df = clients_df.copy()
        clients_df["last_order_date"] = pd.to_datetime(clients_df["last_order_date"], format="%Y-%m-%d", errors="coerce")

        rows = [
            (0, r2_n - 1),
            (r2_n, r3_n - 1),
            (r3_n, r4_n - 1),
            (r4_n, max_r),
        ]
        total_clients = clients_df.shape[0]
        recency_counts = []
        for c, po in rows:
            date_from = end_date - timedelta(days=po)
            date_to = end_date - timedelta(days=c)
            count = clients_df[
                (clients_df["last_order_date"] >= date_from) &
                (clients_df["last_order_date"] <= date_to)
            ].shape[0]
            recency_counts.append(count)
        recency_shares = [f"{(count / total_clients * 100):.2f}%" if total_clients > 0 else "0.00%" for count in recency_counts]

    recency_data = [
        {"дата - с": (end_date - timedelta(days=r2_n - 1)).strftime("%Y-%m-%d"), "с": 0, "по": r2_n - 1, "Кол-во клиентов": recency_counts[0], "Доля": recency_shares[0], "№ сегмента R": 1},
        {"дата - с": (end_date - timedelta(days=r3_n - 1)).strftime("%Y-%m-%d"), "с": r2_n, "по": r3_n - 1, "Кол-во клиентов": recency_counts[1], "Доля": recency_shares[1], "№ сегмента R": 2},
        {"дата - с": (end_date - timedelta(days=r4_n - 1)).strftime("%Y-%m-%d"), "с": r3_n, "по": r4_n - 1, "Кол-во клиентов": recency_counts[2], "Доля": recency_shares[2], "№ сегмента R": 3},
        {"дата - с": (end_date - timedelta(days=max_r - 1)).strftime("%Y-%m-%d"), "с": r4_n, "по": max_r, "Кол-во клиентов": recency_counts[3], "Доля": recency_shares[3], "№ сегмента R": 4},
    ]
    st.subheader("Кол-во клиентов, сделавших последнюю покупку в период \"с - по\" дней назад (Recency)")
    st.dataframe(recency_data, use_container_width=True, hide_index=True)

    # Assign Recency_Segment to clients
    if clients_df is not None and not clients_df.empty:
        recency_dates_sorted = sorted([(pd.to_datetime(row["дата - с"]), row["№ сегмента R"]) for row in recency_data], reverse=True)
        def get_recency_segment(last_order):
            for date_val, segment in recency_dates_sorted:
                if last_order >= date_val:
                    return segment
            return recency_data[-1]["№ сегмента R"]
        clients_df["Recency_Segment"] = clients_df["last_order_date"].apply(get_recency_segment)

        # Save Recency_Segment to database
        _save_segment_column(clients_df, "Recency_Segment")

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

    frequency_counts = []
    frequency_shares = []
    if clients_df is not None and not clients_df.empty and "num_orders" in clients_df.columns:
        total_orders_clients = clients_df.shape[0]
        freq_rows = [
            (1, f2_n - 1),
            (f2_n, f3_n - 1),
            (f3_n, f4_n - 1),
            (f4_n, max_orders),
        ]
        for min_n, max_n in freq_rows:
            count = clients_df[
                (clients_df["num_orders"] >= min_n) &
                (clients_df["num_orders"] <= max_n)
            ].shape[0]
            frequency_counts.append(count)
            share = f"{(count / total_orders_clients * 100):.2f}%" if total_orders_clients > 0 else "0.00%"
            frequency_shares.append(share)
    else:
        frequency_counts = [0, 0, 0, 0]
        frequency_shares = ["0.00%", "0.00%", "0.00%", "0.00%"]

    frequency_data = [
        {"min n": 1, "max n": f2_n - 1, "Кол-во клиентов": frequency_counts[0], "Доля": frequency_shares[0], "№ сегмента F": 4},
        {"min n": f2_n, "max n": f3_n - 1, "Кол-во клиентов": frequency_counts[1], "Доля": frequency_shares[1], "№ сегмента F": 3},
        {"min n": f3_n, "max n": f4_n - 1, "Кол-во клиентов": frequency_counts[2], "Доля": frequency_shares[2], "№ сегмента F": 2},
        {"min n": f4_n, "max n": max_orders, "Кол-во клиентов": frequency_counts[3], "Доля": frequency_shares[3], "№ сегмента F": 1},
    ]
    st.subheader("Кол-во клиентов, сделавших n покупок (Frequency)")
    st.dataframe(frequency_data, use_container_width=True, hide_index=True)

    # Assign Frequency_Segment to clients
    if clients_df is not None and not clients_df.empty:
        freq_max_sorted = sorted([(row["max n"], row["№ сегмента F"]) for row in frequency_data], key=lambda x: x[0])
        def get_frequency_segment(num_orders_val):
            for max_n, segment in freq_max_sorted:
                if num_orders_val <= max_n:
                    return segment
            return frequency_data[-1]["№ сегмента F"]
        clients_df["Frequency_Segment"] = clients_df["num_orders"].apply(get_frequency_segment)

        # Save Frequency_Segment to database
        _save_segment_column(clients_df, "Frequency_Segment")

    st.divider()

    st.subheader("Задаем суммы покупок для сегментов M - Monetary")

    # Параметры счетчиков (только Decimal)
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
    if max_float_m2 < min_float_m2:
        max_float_m2 = min_float_m2
    if max_float_m3 < min_float_m3:
        max_float_m3 = min_float_m3
    if max_float_m4 < min_float_m4:
        max_float_m4 = min_float_m4
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
    monetary_counts = []
    monetary_shares = []
    if clients_df is not None and not clients_df.empty and "total_amount" in clients_df.columns:
        total_monetary_clients = clients_df.shape[0]
        m_rows = [
            (Decimal("0.01"), m2_d - COUNTER_STEP),
            (m2_d, m3_d - COUNTER_STEP),
            (m3_d, m4_d - COUNTER_STEP),
            (m4_d, max_monetary),
        ]
        for c_val, po_val in m_rows:
            count = clients_df[
                (clients_df["total_amount"] >= c_val) &
                (clients_df["total_amount"] <= po_val)
            ].shape[0]
            monetary_counts.append(count)
            share = f"{(count / total_monetary_clients * 100):.2f}%" if total_monetary_clients > 0 else "0.00%"
            monetary_shares.append(share)
    else:
        monetary_counts = [0, 0, 0, 0]
        monetary_shares = ["0.00%", "0.00%", "0.00%", "0.00%"]

    table_data = [
        {"с": Decimal("0.01"), "по": m2_d - COUNTER_STEP, "Кол-во клиентов": monetary_counts[0], "Доля": monetary_shares[0], "№ сегмента M": 4},
        {"с": m2_d, "по": m3_d - COUNTER_STEP, "Кол-во клиентов": monetary_counts[1], "Доля": monetary_shares[1], "№ сегмента M": 3},
        {"с": m3_d, "по": m4_d - COUNTER_STEP, "Кол-во клиентов": monetary_counts[2], "Доля": monetary_shares[2], "№ сегмента M": 2},
        {"с": m4_d, "по": max_monetary, "Кол-во клиентов": monetary_counts[3], "Доля": monetary_shares[3], "№ сегмента M": 1},
    ]
    st.subheader("Кол-во клиентов, сделавших покупок на сумму \"с - по\" (Monetary)")
    st.dataframe([{"с": str(row["с"].quantize(COUNTER_STEP)), "по": str(row["по"].quantize(COUNTER_STEP)), "Кол-во клиентов": row["Кол-во клиентов"], "Доля": row["Доля"], "№ сегмента M": row["№ сегмента M"]} for row in table_data], use_container_width=True, hide_index=True)

    # Assign Monetary_Segment to clients
    if clients_df is not None and not clients_df.empty:
        m_po_sorted = sorted([(row["по"], row["№ сегмента M"]) for row in table_data], key=lambda x: x[0])
        def get_monetary_segment(total_amount_val):
            for po_val, segment in m_po_sorted:
                if total_amount_val <= po_val:
                    return segment
            return table_data[-1]["№ сегмента M"]
        clients_df["Monetary_Segment"] = clients_df["total_amount"].apply(get_monetary_segment)

        # Save Monetary_Segment to database
        _save_segment_column(clients_df, "Monetary_Segment")

    # RF Matrix
    st.divider()
    st.subheader("RF матрица")
    if clients_df is not None and not clients_df.empty and "Frequency_Segment" in clients_df.columns and "Recency_Segment" in clients_df.columns:
        r_values = [4, 3, 2, 1]
        f_values = [1, 2, 3, 4]
        headers = ["FR"] + [f"R-{r}" for r in r_values]
        rows_data = []
        for f in f_values:
            row = [f]
            for r in r_values:
                count = clients_df[(clients_df["Frequency_Segment"] == f) & (clients_df["Recency_Segment"] == r)].shape[0]
                row.append(count)
            rows_data.append(row)
        color_map = {
            (1, 4): "#999999", (1, 3): "#FF8C00", (1, 2): "#FF8C00", (1, 1): "#FFD700",
            (2, 4): "#999999", (2, 3): "#FF7043", (2, 2): "#42A5F5", (2, 1): "#42A5F5",
            (3, 4): "#999999", (3, 3): "#FF7043", (3, 2): "#42A5F5", (3, 1): "#42A5F5",
            (4, 4): "#999999", (4, 3): "#26A69A", (4, 2): "#42A5F5", (4, 1): "#66BB6A",
        }
        text_color_map = {
            "#999999": "white", "#FF8C00": "white", "#FFD700": "black",
            "#FF7043": "white", "#42A5F5": "white", "#26A69A": "white", "#66BB6A": "white",
        }
        st.markdown("""
        <style>
        .rf-matrix table {border-collapse: collapse; width: 100%;}
        .rf-matrix th, .rf-matrix td {border: 1px solid #ddd; padding: 8px; text-align: center;}
        .rf-matrix th {background-color: #262730; color: white;}
        .rf-matrix td:first-child {background-color: #262730; color: white; font-weight: bold;}
        </style>
        <div class="rf-matrix">
        <table>
        <tr><th>FR</th><th>R-4</th><th>R-3</th><th>R-2</th><th>R-1</th></tr>
        """ + "".join(
            f"<tr><td>F-{row[0]}</td>" + "".join(
                f"<td style=\"background:{color_map[(row[0], r_val)]}; color:{text_color_map[color_map[(row[0], r_val)]]};\">{val}</td>"
                for r_val, val in zip([4, 3, 2, 1], row[1:])
            ) + "</tr>"
            for row in rows_data
        ) + """
        </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="rf-legend">
        <b>Легенда RF матрицы</b>
        <table>
        <tr><th></th><th>R-4</th><th>R-3</th><th>R-2</th><th>R-1</th></tr>
        <tr><td><b>F-1</b></td><td style="background:#999999; color:white;">Ушедшие</td><td style="background:#FF8C00; color:white;">Уходящие VIP</td><td style="background:#FF8C00; color:white;">Уходящие VIP</td><td style="background:#FFD700; color:black;">VIP</td></tr>
        <tr><td><b>F-2</b></td><td style="background:#999999; color:white;">Ушедшие</td><td style="background:#FF7043; color:white;">Уходящие</td><td style="background:#42A5F5; color:white;">Норма</td><td style="background:#42A5F5; color:white;">Норма</td></tr>
        <tr><td><b>F-3</b></td><td style="background:#999999; color:white;">Ушедшие</td><td style="background:#FF7043; color:white;">Уходящие</td><td style="background:#42A5F5; color:white;">Норма</td><td style="background:#42A5F5; color:white;">Норма</td></tr>
        <tr><td><b>F-4</b></td><td style="background:#999999; color:white;">Ушедшие</td><td style="background:#26A69A; color:white;">Одноразовые</td><td style="background:#42A5F5; color:white;">Норма</td><td style="background:#66BB6A; color:white;">Новички</td></tr>
        </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="rf-marketing">
        <b>Примеры маркетинговых активностей по сегментам</b>
        <table>
        <tr><th>RF сегмент</th><th>Маркетинговые активности</th></tr>
        <tr><td style="background:#66BB6A; color:white;">Новички</td><td>Научить пользоваться</td></tr>
        <tr><td style="background:#42A5F5; color:white;">Норма</td><td>Обычный режим промоактивности</td></tr>
        <tr><td style="background:#FFD700; color:black;">VIP</td><td>Приглашение в клуб</td></tr>
        <tr><td style="background:#FF8C00; color:white;">Уходящие VIP</td><td>Программы лояльности, Удержание, Реактивация</td></tr>
        <tr><td style="background:#26A69A; color:white;">Одноразовые</td><td>Напоминание, Реактивация</td></tr>
        <tr><td style="background:#FF7043; color:white;">Уходящие</td><td>Реактивация</td></tr>
        <tr><td style="background:#999999; color:white;">Ушедшие</td><td>Прекратить промоактивность, пометить в базе ушедшими</td></tr>
        </table>
        </div>
        """, unsafe_allow_html=True)
