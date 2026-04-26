# AGENTS.md

## Project Structure

- `app.py` - Main Streamlit application entry point
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

## Dependencies

- PostgreSQL (for data storage)
- Streamlit, Pandas, Plotly, psycopg2-binary, openpyxl, SQLAlchemy

## Data Templates

- `data/sales_template.xlsx` - Sales data
- `data/promotion_costs_template.xlsx` - Promotion costs
- `data/other_marketing_costs_template.xlsx` - Other marketing costs