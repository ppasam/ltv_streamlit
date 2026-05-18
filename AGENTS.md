# AGENTS.md

## Project Structure

- `app.py` - Main Streamlit application entry point
- `ui.py` - Streamlit UI components including RFM analysis
- `data_loader.py` - Data loading and PostgreSQL caching module
- `cohorts.py` - Cohort calculation logic with bidirectional recalculation
- `analysis.py` - Data analysis functions (overall, RFM, cohort)
- `plotting.py` - Plotly visualization functions
- `data/` - Excel data templates

## Running the Application

```bash
docker compose up -d --build
```

Access Streamlit at http://localhost:8501

## Critical: Docker Rebuild Required

**Every code change requires rebuild:**
```bash
docker compose up -d --build
```
Simply refreshing the browser will NOT show changes. The container must be rebuilt.

## Dependencies

- PostgreSQL (for data storage)
- Streamlit, Pandas, Plotly, psycopg2-binary, openpyxl, SQLAlchemy

## Data Templates

- `data/sales_template.xlsx` - Sales data
- `data/promotion_costs_template.xlsx` - Promotion costs
- `data/other_marketing_costs_template.xlsx` - Other marketing costs

## Versions

- v0.1.1 - Current (Cohort analysis tables and stacked area chart)
- Previous: v0.0.25 (RFM with Frequency table)

## PostgreSQL Tables

`clients`, `cohorts`, `other_marketing_costs`, `promotion_costs`, `sales`

### clients table columns

`client_id`, `num_orders`, `first_order_date`, `last_order_date`, `total_amount`, `first_order_id`, `first_order_channel`, `cohort`, `Recency_Segment`, `Frequency_Segment`, `Monetary_Segment`

Note: `last_order_date` and `first_order_date` stored as `text` in DB, parse with `format="%Y-%m-%d"` in pandas.

## RFM Analysis - Session State Keys

Each R/F/M section has its own independent session state keys to avoid collisions:

| Section | session_state keys | number_input keys |
|---------|-------------------|-------------------|
| Recency | `rfm_values_r`, `rfm_key_r` | `r2_{key}`, `r3_{key}`, `r4_{key}` |
| Frequency | `rfm_values_f`, `rfm_key_f` | `f2_{key}`, `f3_{key}`, `f4_{key}` |
| Monetary | `monetary_values_m`, `monetary_key_m`, `monetary_prev_values_m` | `monetary_m2_{key}`, `monetary_m3_{key}`, `monetary_m4_{key}` |

## Monetary - Decimal Calculations

All financial calculations use `Decimal` with `ROUND_HALF_UP`. Float is used only for Streamlit number_input display. Pattern:

```python
from decimal import Decimal, ROUND_HALF_UP
COUNTER_STEP = Decimal("0.01")
m2_raw = st.number_input(...)  # float
m2_d = Decimal(str(m2_raw)).quantize(COUNTER_STEP, rounding=ROUND_HALF_UP)
```

## Monetary - Min/Float Trick

Streamlit's button deactivation uses `<=` (not `<`). To allow minus button when value is 0.03, min must be below the value. Use per-segment float mins slightly below Decimal min. Also handle edge case when max < min:

```python
min_float_m2 = float(Decimal("0.019"))
max_float_m2 = max(min_float_m2, float(max_monetary - Decimal("0.02")))
if max_float_m2 < min_float_m2:
    max_float_m2 = min_float_m2
```

## Monetary - Propagation Logic

When a Monetary counter changes, neighboring counters auto-adjust to maintain:
1. `max_monetary >= m4 >= m3 >= m2`
2. Min difference between neighbors: 0.01

Uses `monetary_prev_values_m` to detect which counter changed, then propagates up/down.

## Monetary - Default Values

If `max_monetary_per_customer > 25000`: defaults are `[3000.00, 10000.00, 25000.00]`
Otherwise: defaults are `[a-0.02, a-0.01, a]` where `a = max_monetary`

## Recency - Max from Date Range

`render_rfm_analysis(start_date, end_date)` takes date parameters. Max days for R section:
```python
max_r = (end_date - start_date).days
```

## Recency - Table Column "дата - с"

Calculated as `end_date - timedelta(days=по)` for each row.

## Recency - "Кол-во клиентов" Calculation

For each row, dates are calculated from `end_date` and columns `с`, `по`:
- `date_from = end_date - timedelta(days=по)` — lower bound
- `date_to = end_date - timedelta(days=с)` — upper bound

Count clients where `last_order_date` is in range `[date_from, date_to]`. Example row с=0, по=29:
- `date_from = 2014-12-31 - 29 = 2014-12-02`
- `date_to = 2014-12-31 - 0 = 2014-12-31`

## Frequency - Segment Assignment

For each client, `Frequency_Segment` = first `№ сегмента F` where `num_orders <= max_n` (sorted ascending by max_n).

## Monetary - Segment Assignment

For each client, `Monetary_Segment` = first `№ сегмента M` where `total_amount <= по` (sorted ascending by по).

## RF Matrix

Located after Monetary table. Uses HTML tables with inline CSS for coloring. Color scheme:
- Ушедшие: `#999999` (gray)
- Уходящие VIP: `#FF8C00` (orange)
- VIP: `#FFD700` (gold)
- Уходящие: `#FF7043` (coral)
- Норма: `#42A5F5` (blue)
- Одноразовые: `#26A69A` (teal)
- Новички: `#66BB6A` (green)

## Streamlit Tables - Include All Columns Explicitly

`st.dataframe()` displays only columns explicitly included in the dict/list passed to it. Example:

```python
# WRONG - missing columns
st.dataframe([{"с": ..., "по": ..., "№ сегмента M": ...}])

# CORRECT - all columns included
st.dataframe([{"с": ..., "по": ..., "Кол-во клиентов": ..., "Доля": ..., "№ сегмента M": ...}])
```

## Streamlit - Dynamic Key Rerun Pattern

When counter value changes and needs to propagate, increment key and rerun:
```python
if new_value != old_value:
    st.session_state.some_key = some_key + 1
    st.rerun()
```

This forces Streamlit to re-render with updated constraints.

## Git Workflow

Commits are pushed directly to main. Tags used for releases (e.g., `v0.1.0`).

## Когортный анализ Tables

### "Когорты клиентов" table
- Source: `cohorts` and `clients` tables from DB
- Columns from `cohorts`: `date_start` → "Дата перв. заказа - с", `cohort` → "Номер когорты"
- "Кол-во клиентов": count clients where `date_end >= first_order_date >= date_start`
- "Сумма всех их покупок": sum `total_amount` where same condition, formatted as `$X,XXX.XX`

### "Выручка по когортам" table
- Source: `cohorts` and `sales` tables from DB
- Rows: cohort names from `cohorts.cohort`
- Columns: `date_end` values from `cohorts`
- Cell values: sum `order_price` from `sales` where `date_end >= purchase_date >= date_start` AND `sales.cohort = row_cohort`
- "ВСЕГО" column: sum of all column values per row

### "Количество активных клиентов" table
- Source: `cohorts` and `sales` tables from DB
- Same structure as "Выручка по когортам" (same rows and columns)
- Cell values: `nunique()` count of `client_id` from `sales` where `date_end >= purchase_date >= date_start` AND `sales.cohort = row_cohort`
- Row "ВСЕГО" at bottom with column sums

### "Количество активных клиентов (приведено к началу жизненного цикла)" table
- Same logic as "Количество активных клиентов"
- Columns renamed to "Период 1", "Период 2"... up to "Период N" (where N = number of cohorts)
- Values shifted left: row 1 has N values, row 2 has N-1 values, etc.
- Each row starts from column 2 (period 1) with values from corresponding row of "Количество активных клиентов"

### Stacked Area Chart (plotting.py)
- Function: `create_cohort_revenue_chart(revenue_df)`
- Uses `stackgroup="cohort_revenue"` for stacked area
- Colors from `px.colors.qualitative.Set1/Set2/Dark24`
- Use `hex_to_rgba()` helper (defined in plotting.py) to convert colors to rgba with alpha=0.6
- Legend positioned on the right side

## PostgreSQL Tables Detail

### cohorts
`cohort`, `date_start`, `date_end`

### sales
`purchase_date`, `order_id`, `order_price`, `cost`, `client_id`, `acquisition_channel`, `cohort`

Note: `load_sales_from_db()` renames columns: `purchase_date` → `Date`, `order_price` → `Revenue`, `client_id` → `Customer ID`