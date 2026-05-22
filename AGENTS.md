# AGENTS.md

## Essential Commands

**Run locally (Docker):**
```bash
docker compose up -d --build  # http://localhost:8501
```

**Run all tests:**
```bash
python3 -m pytest test_analysis.py test_cohorts.py test_data_loader.py -v
```

**Lint (analysis.py only):**
```bash
flake8 analysis.py --max-line-length=120
```

## Key Conventions

**Session State (RFM):** Keys namespaced per-section:
- Recency: `rfm_values_r`/`rfm_key_r`
- Frequency: `rfm_values_f`/`rfm_key_f`  
- Monetary: `monetary_values_m`/`monetary_key_m`/`monetary_prev_values_m`

**Database Writes:** Always use batch operations via temp tables (Supabase timeout protection):
```python
cohort_map.to_sql("_tmp", engine, if_exists="replace", index=False)
with engine.begin() as conn:
    conn.execute(text("UPDATE target SET col = t.col FROM _tmp t WHERE ..."))
    conn.execute(text("DROP TABLE IF EXISTS _tmp"))
```

**Performance:** Cohort recalculation only runs when params change (check `_cohort_params` session state). Avoid calling `st.cache_data.clear()` on every render.

## Database
Two deployment modes. Same codebase.

| Mode | DB | DATABASE_URL source |
|------|----|---------------------|
| Local Docker | PostgreSQL container (`ltv_user:ltv_pass@postgres:5432/ltv_db`) | `docker-compose.yml` env |
| Streamlit Cloud | Supabase session pooler | `st.secrets["DATABASE_URL"]` |

Priority: `st.secrets["DATABASE_URL"]` → `os.environ["DATABASE_URL"]` → local default.

**Local Docker specifics:** 
- Service name: `postgres`
- Image: `postgres:15`
- Environment: `POSTGRES_DB=ltv_db`, `POSTGRES_USER=ltv_user`, `POSTGRES_PASSWORD=ltv_pass`
- Ports: `5432:5432`
- Streamlit service connects via: `postgresql://ltv_user:ltv_pass@postgres:5432/ltv_db`

**Git:** Push directly to `main`. Use tags for releases (e.g., `v2.0.4`).

## Gotchas

- `st.dataframe()` only shows explicitly included dict keys — always list all columns
- Counter propagation uses increment-key + `st.rerun()` pattern
- Monetary values use `Decimal` with `ROUND_HALF_UP`; floats only for `st.number_input` display
- `data/download_data/` created on demand via `os.makedirs(exist_ok=True)`
- Segment saves (`Recency_Segment`, `Frequency_Segment`, `Monetary_Segment`) wrapped in try/except (non-critical)

## Module Responsibilities

- `app.py`: Entry point, session init, sidebar, section routing
- `ui_common.py`: Shared UI components (`render_sidebar()`, etc.)
- `ui_general.py`: Overall analysis (`render_overall_analysis()`)
- `ui_rfm.py`: RFM analysis + financial counters
- `ui_cohort.py`: Cohort analysis + CLV calculations
- `data_loader.py`: DB connection, Excel loading, batch operations
- `cohorts.py`: Cohort date math and bidirectional recalculation
- `analysis.py`: Core pandas calculations for tables/charts
- `plotting.py`: Plotly figure generation