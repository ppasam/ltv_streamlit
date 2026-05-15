# AGENTS.md

## Project Structure

- `app.py` - Main Streamlit application entry point
- `data_loader.py` - Data loading and PostgreSQL caching module
- `cohorts.py` - Cohort calculation logic with bidirectional recalculation
- `analysis.py` - Data analysis functions (overall, RFM, cohort)
- `plotting.py` - Plotly visualization functions
- `ui.py` - UI rendering with RFM analysis sections (R, F, M)
- `data/` - Excel data templates

## Running the Application

```bash
docker compose up -d --build
```

Access Streamlit at http://localhost:8501

## Dependencies

- PostgreSQL (for data storage)
- Streamlit, Pandas, Plotly, psycopg2-binary, openpyxl, SQLAlchemy

## Data Templates

- `data/sales_template.xlsx` - Sales data
- `data/promotion_costs_template.xlsx` - Promotion costs
- `data/other_marketing_costs_template.xlsx` - Other marketing costs

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

Streamlit's button deactivation uses `<=` (not `<`). To allow minus button when value is 0.03, min must be below the value. Use per-segment float mins slightly below Decimal min:

```python
min_float_m2 = float(Decimal("0.019"))  # allows minus when value=0.02
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

Commits are pushed directly to main. Tags used for releases (e.g., `v0.0.29`).