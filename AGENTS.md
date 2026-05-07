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

## RFM Analysis (Frequency / Segments)

The RFM analysis uses dynamic widget keys for cascade updates. Key patterns:
- `rfm_key` counter increments on each change  
- Keys like `f2_{key}`, `f3_{key}`, `f4_{key}` force Streamlit to recreate widgets

When editing RFM logic in `ui.py`:
- Always rebuild the container after changes
- Run "Общий анализ" first to populate `max_orders_per_customer` in session_state
- Then switch to "RFM анализ" — this provides dynamic max values for segments

## Dependencies

- PostgreSQL (for data storage)
- Streamlit, Pandas, Plotly, psycopg2-binary, openpyxl, SQLAlchemy

## Data Templates

- `data/sales_template.xlsx` - Sales data
- `data/promotion_costs_template.xlsx` - Promotion costs
- `data/other_marketing_costs_template.xlsx` - Other marketing costs

## Versions

- v0.0.25 - Current (RFM with Frequency table)
- Previous: v0.0.24 (dynamic max values for RFM segments)