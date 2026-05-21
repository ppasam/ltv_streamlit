# AGENTS.md

## Run & Deploy

```bash
# Local (Docker) — rebuild on every code change
docker compose up -d --build          # http://localhost:8501

# Tests
python3 -m pytest test_analysis.py -v

# Lint
flake8 analysis.py --max-line-length=120
```

`app.py` is the entrypoint. Layout: `st.set_page_config(layout="wide")`.

## Database

Two deployment modes. Same codebase.

| Mode | DB | DATABASE_URL source |
|------|----|---------------------|
| Local Docker | PostgreSQL container (`ltv_user:ltv_pass@postgres:5432/ltv_db`) | `docker-compose.yml` env |
| Streamlit Cloud | Supabase session pooler | `st.secrets["DATABASE_URL"]` |

Priority: `st.secrets["DATABASE_URL"]` → `os.environ["DATABASE_URL"]` → local default.

On first run, `check_tables_exist()` checks for `sales` + `clients` tables. If missing, `init_database_from_templates()` loads `data/templates_data/*.xlsx` → Supabase.

### Tables

| Table | Key columns | Notes |
|-------|-------------|-------|
| `sales` | `purchase_date`, `order_price`, `client_id`, `acquisition_channel`, `cohort` | Renamed on load: `purchase_date`→`Date`, `order_price`→`Revenue`, `client_id`→`Customer ID` |
| `clients` | `client_id`, `num_orders`, `first_order_date`, `last_order_date`, `total_amount`, `cohort` | Dates stored as TEXT, parse with `format="%Y-%m-%d"` |
| `cohorts` | `cohort`, `date_start`, `date_end` | Supabase returns dates as str → `pd.to_datetime()` before use |
| `promotion_costs` | `channels`, `expenses_date`, `costs`, `cohort` | — |
| `other_marketing_costs` | `channels`, `expenses_date`, `costs`, `cohort` | — |

### Batch SQL Pattern (Supabase timeouts)

All DB writes use batch operations via temp tables. Never row-by-row:

```python
cohort_map.to_sql("_tmp", engine, if_exists="replace", index=False)
with engine.begin() as conn:
    conn.execute(text("UPDATE target SET col = t.col FROM _tmp t WHERE ..."))
    conn.execute(text("DROP TABLE IF EXISTS _tmp"))
```

Segment saves (`Recency_Segment`, `Frequency_Segment`, `Monetary_Segment`) are wrapped in try/except — non-critical.

### Performance

Cohort recalculation (`update_cohorts_in_db` + `populate_clients_from_sales`) only runs when params change (`_cohort_params` session state key). `st.cache_data.clear()` is NOT called on every page render.

`load_cohorts_from_db()` and `load_sales_from_db()` are `@st.cache_data(ttl=3600)`.

## Modules

| File | Responsibility |
|------|---------------|
| `app.py` | Session init, sidebar, section routing |
| `ui.py` | All Streamlit rendering (4 sections: Общий/RFM/Когортный/Загрузка) |
| `data_loader.py` | DB connection, Excel loading, init, batch writes |
| `cohorts.py` | Cohort math: date splitting, bidirectional recalculation |
| `analysis.py` | Pandas calculations for all tables/charts |
| `plotting.py` | Plotly figures (`hex_to_rgba`, stacked area, pie, bar) |

## RFM Analysis

- **Session state keys are per-section** to avoid collisions: Recency uses `rfm_values_r`/`rfm_key_r`, Frequency uses `rfm_values_f`/`rfm_key_f`, Monetary uses `monetary_values_m`/`monetary_key_m`/`monetary_prev_values_m`.
- **Monetary** uses `Decimal` with `ROUND_HALF_UP`. Float only for `st.number_input` display. Propagation rule: `max >= m4 >= m3 >= m2` with 0.01 min step.
- **RF Matrix** is rendered as raw HTML tables with inline CSS (colors in AGENTS.md table section).
- **Segment columns** in `clients` table are recomputed in-memory each render; DB save is optional.

## Key Gotchas

- `st.dataframe()` only shows explicitly included dict keys — always list all columns.
- Counter propagation uses increment-key + `st.rerun()` pattern.
- Git: push directly to `main`, no PR workflow. Tags for releases.
- `data/download_data/` is created on demand via `os.makedirs(exist_ok=True)`.
