"""Когортный анализ section for LTV Streamlit application."""
from datetime import timedelta

import pandas as pd
import streamlit as st

import data_loader
import plotting


def _cohort_period_table(
    cohort_names: list,
    column_headers: list,
    cohort_map: dict,
    value_fn
) -> list:
    """Build a cohort × period table.

    value_fn(cohort_name, date_start, date_end) → (display_value, numeric_inc)
    Returns list of {Когорты, col..., _total}.
    """
    table = []
    for cohort_name in cohort_names:
        row = {"Когорты": cohort_name}
        total = 0.0
        for col in column_headers:
            coh = cohort_map[col]
            date_start = pd.to_datetime(coh["date_start"])
            date_end = pd.to_datetime(coh["date_end"])
            val, inc = value_fn(cohort_name, date_start, date_end)
            row[col] = val
            total += inc
        row["_total"] = total
        table.append(row)
    return table


def render_cohort_analysis(cohort_dates: list) -> None:
    """Render Когортный анализ section."""
    st.header("Когортный анализ")

    cohorts_df = data_loader.load_cohorts_from_db()
    for col in ["date_start", "date_end"]:
        if col in cohorts_df.columns and not pd.api.types.is_datetime64_any_dtype(cohorts_df[col]):
            cohorts_df[col] = pd.to_datetime(cohorts_df[col])
    clients_df = data_loader.load_clients_from_db()

    if not clients_df.empty and "first_order_date" in clients_df.columns:
        clients_df = clients_df.copy()
        clients_df["first_order_date_dt"] = pd.to_datetime(clients_df["first_order_date"], format="%Y-%m-%d", errors="coerce")

    st.subheader("Когорты клиентов")
    cohort_table = []
    for _, coh_row in cohorts_df.iterrows():
        date_start = pd.to_datetime(coh_row["date_start"])
        date_end = pd.to_datetime(coh_row["date_end"])

        if not clients_df.empty and "first_order_date_dt" in clients_df.columns:
            mask = (clients_df["first_order_date_dt"] >= date_start) & (clients_df["first_order_date_dt"] <= date_end)
            client_count = int(clients_df[mask].shape[0])
            total_sum = f"${float(clients_df.loc[mask, 'total_amount'].sum()):,.2f}" if "total_amount" in clients_df.columns else ""
        else:
            client_count = ""
            total_sum = ""

        cohort_table.append({
            "Дата перв. заказа - с": date_start.strftime("%Y-%m-%d"),
            "Номер когорты": coh_row["cohort"],
            "Кол-во клиентов": client_count,
            "Сумма всех их покупок": total_sum
        })

    st.dataframe(cohort_table, use_container_width=True, hide_index=True)

    st.subheader("Выручка по когортам")
    sales_df = data_loader.load_sales_from_db()

    if not sales_df.empty and "Date" in sales_df.columns:
        sales_df = sales_df.copy()
        sales_df["purchase_date_dt"] = pd.to_datetime(sales_df["Date"], errors="coerce")

    if not clients_df.empty and "last_order_date" in clients_df.columns:
        clients_df = clients_df.copy()
        clients_df["last_order_date_dt"] = pd.to_datetime(clients_df["last_order_date"], format="%Y-%m-%d", errors="coerce")

    cohort_map = {coh_row["date_end"].strftime("%Y-%m-%d"): coh_row for _, coh_row in cohorts_df.iterrows()}
    column_headers = [coh_row["date_end"].strftime("%Y-%m-%d") for _, coh_row in cohorts_df.iterrows()]
    cohort_names = [coh_row["cohort"] for _, coh_row in cohorts_df.iterrows()]

    has_sales = not sales_df.empty and "purchase_date_dt" in sales_df.columns and "cohort" in sales_df.columns

    revenue_table = _cohort_period_table(
        cohort_names, column_headers, cohort_map,
        lambda c, ds, de: (
            (lambda rev: (f"${rev:,.2f}" if rev > 0 else "", rev))(
                float(sales_df.loc[(sales_df["purchase_date_dt"] >= ds) & (sales_df["purchase_date_dt"] <= de) & (sales_df["cohort"] == c), "Revenue"].sum())
            ) if has_sales and "Revenue" in sales_df.columns
            else ("", 0.0)
        )
    )
    for row in revenue_table:
        t = row.pop("_total")
        row["ВСЕГО"] = f"${t:,.2f}" if t > 0 else ""

    revenue_table_df = pd.DataFrame(revenue_table)
    st.dataframe(revenue_table_df, use_container_width=True, hide_index=True)

    revenue_chart = plotting.create_cohort_revenue_chart(revenue_table_df)
    if revenue_chart:
        st.plotly_chart(revenue_chart, use_container_width=True)

    st.subheader("Количество активных клиентов")
    active_clients_table = _cohort_period_table(
        cohort_names, column_headers, cohort_map,
        lambda c, ds, de: (
            (lambda n: (n if n > 0 else "", n))(
                int(sales_df.loc[(sales_df["purchase_date_dt"] >= ds) & (sales_df["purchase_date_dt"] <= de) & (sales_df["cohort"] == c), "Customer ID"].nunique())
            ) if has_sales and "Customer ID" in sales_df.columns
            else ("", 0)
        )
    )
    for row in active_clients_table:
        t = row.pop("_total")
        for col in column_headers:
            if row[col] == "" or row[col] == 0:
                row[col] = ""
        row["ВСЕГО"] = t if t > 0 else ""

    total_row = {"Когорты": "ВСЕГО"}
    for col in column_headers:
        col_sum = sum(r.get(col, 0) for r in active_clients_table if isinstance(r.get(col, 0), (int, float)))
        total_row[col] = col_sum if col_sum > 0 else ""
    # Calculate sum of "ВСЕГО" column for the total row
    total_of_totals = sum(
        int(r.get("ВСЕГО", 0)) 
        for r in active_clients_table 
        if isinstance(r.get("ВСЕГО"), (int, float)) or (isinstance(r.get("ВСЕГО"), str) and r.get("ВСЕГО") != "" and r.get("ВСЕГО").replace(",", "").replace("$", "").isdigit())
    )
    # Handle formatted currency strings in "ВСЕГО" column
    if total_of_totals == 0:
        total_of_totals = sum(
            float(str(r.get("ВСЕГО", "")).replace("$", "").replace(",", "")) 
            for r in active_clients_table 
            if isinstance(r.get("ВСЕГО"), str) and r.get("ВСЕГО") != "" and str(r.get("ВСЕГО")).replace("$", "").replace(",", "").replace(".", "", 1).isdigit()
        )
    total_row["ВСЕГО"] = f"{int(total_of_totals):,}" if total_of_totals > 0 else ""
    active_clients_table.append(total_row)

    active_clients_table_df = pd.DataFrame(active_clients_table)
    st.dataframe(active_clients_table_df, use_container_width=True, hide_index=True)

    st.subheader("Количество активных клиентов (приведено к началу жизненного цикла)")
    num_cohorts = len(cohort_names)
    period_names = [f"Период {i+1}" for i in range(num_cohorts)]
    normalized_table = []
    for row_idx, cohort_name in enumerate(cohort_names):
        row = {"Когорты": cohort_name}
        source_row = active_clients_table[row_idx]
        for period_idx, period_name in enumerate(period_names):
            source_col_idx = row_idx + period_idx
            if source_col_idx < num_cohorts:
                source_col = column_headers[source_col_idx]
                val = source_row.get(source_col, "")
                row[period_name] = val if val != "" else ""
            else:
                row[period_name] = ""
        normalized_table.append(row)

    normalized_table_df = pd.DataFrame(normalized_table)
    st.dataframe(normalized_table_df, use_container_width=True, hide_index=True)

    st.subheader("Индекс активных клиентов (кол-во активных в когорте в перв. период = 1)")
    index_table = []
    for row in normalized_table:
        index_row = {"Когорты": row["Когорты"]}
        first_period_val = row.get("Период 1", 0)
        if first_period_val == "" or first_period_val == 0:
            for period_name in period_names:
                index_row[period_name] = ""
        else:
            for period_name in period_names:
                val = row.get(period_name, "")
                if val == "" or val == 0:
                    index_row[period_name] = ""
                else:
                    index_row[period_name] = round(val / first_period_val, 2)
        index_table.append(index_row)

    index_table_df = pd.DataFrame(index_table)
    st.dataframe(index_table_df, use_container_width=True, hide_index=True)

    index_chart = plotting.create_client_index_chart(index_table_df)
    if index_chart:
        st.plotly_chart(index_chart, use_container_width=True)

    st.subheader("Средняя выручка на покупателя (приведено к началу жизненного цикла)")
    avg_revenue_table = []
    for row_idx, cohort_name in enumerate(cohort_names):
        avg_row = {"Когорты": cohort_name}
        for period_idx in range(num_cohorts):
            source_col_idx = row_idx + period_idx
            if source_col_idx < num_cohorts:
                col = column_headers[source_col_idx]
                rev_val = revenue_table[row_idx].get(col, "")
                clients_val = active_clients_table[row_idx].get(col, "")
                if rev_val != "" and clients_val != "" and clients_val != 0:
                    rev_num = float(str(rev_val).replace("$", "").replace(",", ""))
                    avg_val = rev_num / clients_val
                    avg_row[f"Период {period_idx + 1}"] = f"${avg_val:,.2f}"
                else:
                    avg_row[f"Период {period_idx + 1}"] = ""
            else:
                avg_row[f"Период {period_idx + 1}"] = ""
        avg_revenue_table.append(avg_row)

    for row_idx, row in enumerate(avg_revenue_table):
        if row["Когорты"] != "Средневзвешенная":
            total_rev_val = revenue_table[row_idx].get("ВСЕГО", "")
            total_clients_sum = sum(
                int(active_clients_table[row_idx].get(col, 0))
                for col in column_headers
                if active_clients_table[row_idx].get(col, "") != ""
            )
            if total_rev_val != "" and total_clients_sum > 0:
                rev_num = float(str(total_rev_val).replace("$", "").replace(",", ""))
                row["В среднем"] = f"${rev_num / total_clients_sum:,.2f}"
            else:
                row["В среднем"] = ""
        else:
            row["В среднем"] = ""

    weighted_row = {"Когорты": "Средневзвешенная"}
    for period_idx in range(num_cohorts):
        total_rev = 0.0
        total_clients = 0
        for row_idx in range(num_cohorts - period_idx):
            col = column_headers[row_idx + period_idx]
            rev_val = revenue_table[row_idx].get(col, "")
            clients_val = active_clients_table[row_idx].get(col, "")
            if rev_val != "" and clients_val != "" and clients_val != 0:
                total_rev += float(str(rev_val).replace("$", "").replace(",", ""))
                total_clients += clients_val
        if total_clients > 0:
            weighted_row[f"Период {period_idx + 1}"] = f"${total_rev / total_clients:,.2f}"
        else:
            weighted_row[f"Период {period_idx + 1}"] = ""
    total_rev_all = 0.0
    total_clients_all = 0
    for row_idx in range(num_cohorts):
        rev_val = revenue_table[row_idx].get("ВСЕГО", "")
        if rev_val != "":
            total_rev_all += float(str(rev_val).replace("$", "").replace(",", ""))
        for col in column_headers:
            clients_val = active_clients_table[row_idx].get(col, "")
            if clients_val != "":
                total_clients_all += int(clients_val)
    if total_clients_all > 0:
        weighted_row["В среднем"] = f"${total_rev_all / total_clients_all:,.2f}"
    else:
        weighted_row["В среднем"] = ""
    avg_revenue_table.append(weighted_row)

    avg_revenue_table_df = pd.DataFrame(avg_revenue_table)
    st.dataframe(avg_revenue_table_df, use_container_width=True, hide_index=True)

    avg_revenue_chart = plotting.create_avg_revenue_chart(avg_revenue_table_df)
    if avg_revenue_chart:
        st.plotly_chart(avg_revenue_chart, use_container_width=True)

    st.subheader("Количество ушедших клиентов")
    churn_table = []
    rfm_vals_r = st.session_state.get("rfm_values_r", [30, 90, 365])
    r4_n = rfm_vals_r[2]

    for row_idx, cohort_name in enumerate(cohort_names):
        churn_row = {"Когорты": cohort_name}
        for col in column_headers:
            col_cohort = cohort_map[col]
            date_end = pd.to_datetime(col_cohort["date_end"])

            if not clients_df.empty and "last_order_date_dt" in clients_df.columns and "cohort" in clients_df.columns:
                threshold_date = date_end - timedelta(days=r4_n)
                mask = (clients_df["cohort"] == cohort_name) & (clients_df["last_order_date_dt"] <= threshold_date)
                churn_count = int(clients_df[mask].shape[0])
            else:
                churn_count = 0

            churn_row[col] = churn_count if churn_count > 0 else ""
        churn_table.append(churn_row)

    for row in churn_table:
        prev_val = ""
        for i in range(len(column_headers)):
            if i >= 2:
                curr_val = row[column_headers[i]]
                if curr_val != "" and prev_val != "":
                    diff = curr_val - prev_val
                    row[column_headers[i]] = diff if diff > 0 else ""
                prev_val = curr_val if curr_val != "" else prev_val

    for row in churn_table:
        total = sum(v for v in row.values() if isinstance(v, (int, float)) and v != "")
        row["ВСЕГО"] = total if total > 0 else ""

    total_row = {"Когорты": "ВСЕГО"}
    for col in column_headers:
        col_sum = sum(int(row[col]) for row in churn_table if isinstance(row[col], (int, float)) and row[col] != "")
        total_row[col] = col_sum if col_sum > 0 else ""
    total_row["ВСЕГО"] = sum(int(row["ВСЕГО"]) for row in churn_table if isinstance(row["ВСЕГО"], (int, float)) and row["ВСЕГО"] != "")
    churn_table.append(total_row)

    churn_table_df = pd.DataFrame(churn_table)
    st.dataframe(churn_table_df, use_container_width=True, hide_index=True)

    st.subheader("Количество актуальных (оставшихся) клиентов")
    churn_data = churn_table[:-1] if churn_table else []
    actual_table = []
    for row_idx, cohort_name in enumerate(cohort_names):
        actual_row = {"Когорты": cohort_name}
        prev_actual = cohort_table[row_idx]["Кол-во клиентов"] if row_idx < len(cohort_table) else 0
        for i, col in enumerate(column_headers):
            if i == row_idx:
                actual_row[col] = prev_actual
            elif i > row_idx:
                churn_val = 0
                if row_idx < len(churn_data) and col in churn_data[row_idx]:
                    cv = churn_data[row_idx].get(col, 0)
                    churn_val = cv if isinstance(cv, (int, float)) else 0
                new_val = prev_actual - churn_val
                actual_row[col] = new_val if new_val > 0 else ""
                prev_actual = new_val if new_val > 0 else prev_actual
            else:
                actual_row[col] = ""
        actual_table.append(actual_row)

    actual_table_data = actual_table

    total_row = {"Когорты": "ВСЕГО"}
    for col in column_headers:
        col_sum = sum(int(row[col]) for row in actual_table if isinstance(row[col], (int, float)) and row[col] != "")
        total_row[col] = col_sum if col_sum > 0 else ""
    actual_table.append(total_row)

    actual_table_df = pd.DataFrame(actual_table)
    st.dataframe(actual_table_df, use_container_width=True, hide_index=True)

    st.subheader("Churn rate")
    new_columns = ["Когорты"] + [f"Период {i+1}" for i in range(len(column_headers))] + ["В среднем за все время"]
    churn_rate_data = []
    for row in actual_table:
        new_row = {"Когорты": row["Когорты"]}
        for i, col_name in enumerate(new_columns[1:-1]):
            new_row[col_name] = ""
        new_row["В среднем за все время"] = ""
        churn_rate_data.append(new_row)
    churn_rate_df = pd.DataFrame(churn_rate_data)
    churn_rate_df = churn_rate_df.astype(object)
    churn_rate_df.iloc[:, 0] = churn_rate_df.iloc[:, 0].astype(str)

    for row_idx in range(len(actual_table)):
        for col_idx in range(1, len(new_columns)):
            curr_col_idx = col_idx - 1 + row_idx
            prev_col_idx = col_idx - 2 + row_idx
            if curr_col_idx < len(column_headers) and prev_col_idx >= 0 and prev_col_idx < len(column_headers):
                curr_val = actual_table[row_idx].get(column_headers[curr_col_idx], 0)
                prev_val = actual_table[row_idx].get(column_headers[prev_col_idx], 0)
                if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)) and prev_val > 0:
                    churn = 1 - (curr_val / prev_val)
                    if abs(churn) < 0.0001:
                        churn_rate_df.iloc[row_idx, col_idx] = ""
                    else:
                        churn_rate_df.iloc[row_idx, col_idx] = f"{churn * 100:.2f}%"
                else:
                    churn_rate_df.iloc[row_idx, col_idx] = ""
            else:
                churn_rate_df.iloc[row_idx, col_idx] = ""

    def _val(row, col):
        v = row.get(col, 0)
        return v if isinstance(v, (int, float)) else 0

    num_cohorts = len(column_headers)
    for row_idx in range(len(actual_table) - 1):
        k = row_idx + 1
        x = _val(actual_table[row_idx], column_headers[-1])
        y = cohort_table[row_idx]["Кол-во клиентов"] if row_idx < len(cohort_table) else 0
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and y > 0 and k < num_cohorts:
            churn = 1 - (x / y) ** (1 / (num_cohorts - k))
            churn_rate_df.iloc[row_idx, -1] = f"{churn * 100:.2f}%"

    if "ВСЕГО" in churn_rate_df["Когорты"].values:
        for col in churn_rate_df.columns[1:]:
            churn_rate_df.loc[churn_rate_df["Когорты"] == "ВСЕГО", col] = ""

        for period_idx in range(2, len(new_columns)):
            diag_offset = period_idx - 1
            curr_diag_sum = sum(
                _val(actual_table[i], column_headers[i + diag_offset])
                for i in range(len(actual_table) - 1 - diag_offset)
                if i + diag_offset < len(column_headers)
            )
            prev_diag_sum = sum(
                _val(actual_table[i], column_headers[i + diag_offset - 1])
                for i in range(len(actual_table) - 1 - diag_offset)
                if i + diag_offset - 1 < len(column_headers)
            )
            if prev_diag_sum > 0:
                churn = 1 - (curr_diag_sum / prev_diag_sum)
                churn_rate_df.loc[churn_rate_df["Когорты"] == "ВСЕГО", new_columns[period_idx]] = f"{churn * 100:.2f}%"

        values = []
        for row_idx in range(len(actual_table) - 1):
            val = churn_rate_df.iloc[row_idx, -1]
            if val != "" and isinstance(val, str):
                try:
                    values.append(float(val.replace("%", "")))
                except:
                    pass
        if values:
            avg = sum(values) / len(values)
            churn_rate_df.loc[churn_rate_df["Когорты"] == "ВСЕГО", "В среднем за все время"] = f"{avg:.2f}%"

        churn_rate_df.loc[churn_rate_df["Когорты"] == "ВСЕГО", "Когорты"] = "В среднем"

    st.dataframe(churn_rate_df, use_container_width=True, hide_index=True)

    st.subheader("Валовая прибыль по когортам")
    gross_profit_table = _cohort_period_table(
        cohort_names, column_headers, cohort_map,
        lambda c, ds, de: (
            (lambda rev, cost: (f"${rev - cost:,.2f}" if rev - cost > 0 else "", rev - cost))(
                float(sales_df.loc[(sales_df["purchase_date_dt"] >= ds) & (sales_df["purchase_date_dt"] <= de) & (sales_df["cohort"] == c), "Revenue"].sum()) if "Revenue" in sales_df.columns else 0.0,
                float(sales_df.loc[(sales_df["purchase_date_dt"] >= ds) & (sales_df["purchase_date_dt"] <= de) & (sales_df["cohort"] == c), "cost"].sum()) if "cost" in sales_df.columns else 0.0
            ) if has_sales else ("", 0.0)
        )
    )
    for row in gross_profit_table:
        t = row.pop("_total")
        row["ВСЕГО"] = f"${t:,.2f}" if t > 0 else ""

    total_row = {"Когорты": "ВСЕГО"}
    for col in column_headers:
        col_sum = sum(float(row[col].replace("$", "").replace(",", "")) for row in gross_profit_table if isinstance(row[col], str) and row[col])
        total_row[col] = f"${col_sum:,.2f}" if col_sum > 0 else ""
    grand_total = sum(float(row["ВСЕГО"].replace("$", "").replace(",", "")) for row in gross_profit_table if isinstance(row["ВСЕГО"], str) and row["ВСЕГО"])
    total_row["ВСЕГО"] = f"${grand_total:,.2f}" if grand_total > 0 else ""
    gross_profit_table.append(total_row)

    gross_profit_df = pd.DataFrame(gross_profit_table)
    st.dataframe(gross_profit_df, use_container_width=True, hide_index=True)

    st.subheader("Валовая прибыль на одного клиента")
    gp_per_client_table = []
    for row_idx in range(len(gross_profit_table)):
        row = gross_profit_table[row_idx]
        gp_row = {"Когорты": row["Когорты"]}
        for col in column_headers:
            gp_val = row.get(col, "")
            actual_val = actual_table_data[row_idx].get(col, 0)
            if isinstance(gp_val, str) and gp_val and isinstance(actual_val, (int, float)) and actual_val > 0:
                gp_num = float(gp_val.replace("$", "").replace(",", ""))
                per_client = gp_num / actual_val
                gp_row[col] = f"${per_client:,.2f}" if per_client > 0 else ""
            else:
                gp_row[col] = ""
        gp_total_str = row.get("ВСЕГО", "")
        if isinstance(gp_total_str, str) and gp_total_str:
            gp_total_num = float(gp_total_str.replace("$", "").replace(",", ""))
            actual_sum = sum(actual_table_data[row_idx].get(c, 0) for c in column_headers if isinstance(actual_table_data[row_idx].get(c, 0), (int, float)) and actual_table_data[row_idx].get(c, 0) > 0)
            if actual_sum > 0:
                gp_row["ВСЕГО"] = f"${gp_total_num / actual_sum:,.2f}"
            else:
                gp_row["ВСЕГО"] = ""
        else:
            gp_row["ВСЕГО"] = ""
        gp_per_client_table.append(gp_row)
    gp_per_client_df = pd.DataFrame(gp_per_client_table)
    st.dataframe(gp_per_client_df, use_container_width=True, hide_index=True)

    max_cohort_num = len(cohorts_df)
    cohort_number = st.number_input("Выберите номер когорты для расчета CLV", value=1, min_value=1, max_value=max_cohort_num, step=1, key="clv_cohort_number")

    st.subheader("Расчет Customer Lifetime Value (CLV)")
    idx = cohort_number - 1
    avg_profit_per_client = gp_per_client_table[idx].get("ВСЕГО", "") if gp_per_client_table and idx < len(gp_per_client_table) else ""
    churn_rate_val_str = churn_rate_df.iloc[idx]["В среднем за все время"] if not churn_rate_df.empty and "В среднем за все время" in churn_rate_df.columns and idx < len(churn_rate_df) else ""
    churn_rate_val = 0
    if churn_rate_val_str and isinstance(churn_rate_val_str, str) and "%" in churn_rate_val_str:
        try:
            churn_rate_val = float(churn_rate_val_str.replace("%", "")) / 100
        except:
            churn_rate_val = 0
    lifetime_val = f"{1 / churn_rate_val:.2f}" if churn_rate_val > 0 else ""
    avg_profit_val = 0
    if avg_profit_per_client and isinstance(avg_profit_per_client, str) and avg_profit_per_client.startswith("$"):
        try:
            avg_profit_val = float(avg_profit_per_client.replace("$", "").replace(",", ""))
        except:
            avg_profit_val = 0
    clv_val = f"${avg_profit_val / churn_rate_val:,.2f}" if churn_rate_val > 0 else ""
    clv_table = [
        {"Показатель": "Ср. прибыль с клиента за период (по выбранной когорте)", "Значение": avg_profit_per_client},
        {"Показатель": "Churn rate (по выбранной когорте)", "Значение": churn_rate_val_str},
        {"Показатель": "Средняя длительность Lifetime (периодов)", "Значение": lifetime_val},
        {"Показатель": "CLV", "Значение": clv_val}
    ]
    clv_df = pd.DataFrame(clv_table)
    st.dataframe(clv_df, use_container_width=True, hide_index=True)
    st.caption("Комментарий: CLV по валовой прибыли, без дисконтирования стоимости денег")

    col1, col2 = st.columns(2)
    with col1:
        cac_ratio = st.number_input("Задайте соотношение CAC : CLV ratio", value=1, min_value=1, step=1, key="cac_clv_ratio_num")
    with col2:
        clv_ratio = st.number_input("", value=3, min_value=1, step=1, key="cac_clv_ratio_denom")
    clv_numeric = 0
    if clv_val and isinstance(clv_val, str) and clv_val.startswith("$"):
        try:
            clv_numeric = float(clv_val.replace("$", "").replace(",", ""))
        except:
            clv_numeric = 0
    acceptable_cac = clv_numeric * cac_ratio / clv_ratio if clv_ratio > 0 else 0
    st.write(f"**Приемлемый CAC: ${acceptable_cac:,.2f}**")
