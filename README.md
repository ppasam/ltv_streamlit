# LTV Streamlit Application

A Streamlit-based application for analyzing Lifetime Value (LTV) of customers with RFM analysis, cohort analysis, and various business metrics.

## Features

- **RFM Analysis**: Recency, Frequency, Monetary analysis for customer segmentation
- **Cohort Analysis**: Track customer behavior and revenue over time by acquisition cohorts
- **CLV Calculation**: Customer Lifetime Value computation
- **Business Metrics**: Revenue, profit, churn rates, and other key performance indicators
- **Interactive Visualizations**: Plotly charts for data exploration
- **Database Integration**: Supabase/PostgreSQL backend for data persistence

## Project Structure

```
ltv_streamlit/
├── app.py                  # Main application entry point
├── analysis.py             # Core business logic and calculations
├── cohorts.py              # Cohort date handling and math
├── data_loader.py          # Database connection and data loading
├── plotting.py             # Visualization functions (Plotly)
├── ui_common.py            # Shared UI components
├── ui_cohort.py            # Cohort analysis interface
├── ui_general.py           # Overall analysis interface
├── ui_rfm.py               # RFM analysis interface
├── test_analysis.py        # Unit tests for analysis module
├── test_cohorts.py         # Unit tests for cohorts module
├── test_data_loader.py     # Unit tests for data loader
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker configuration for local development
├── Dockerfile              # Container definition
└── README.md               # This file
```

## Installation

### Local Development (Docker)

1. Clone the repository
2. Build and run with Docker Compose:
   ```bash
   docker compose up -d --build
   ```
3. Access the application at http://localhost:8501

### Dependencies

See `requirements.txt` for Python package dependencies.

## Database Configuration

The application supports two deployment modes:

| Mode | Database | Configuration Source |
|------|----------|---------------------|
| Local Docker | PostgreSQL container | `docker-compose.yml` environment variables |
| Streamlit Cloud | Supabase session pooler | `st.secrets["DATABASE_URL"]` |

Priority order for database URL:
1. `st.secrets["DATABASE_URL"]`
2. `os.environ["DATABASE_URL"]`
3. Local default (PostgreSQL container)

## Running Tests

Execute the test suite with:
```bash
python3 -m pytest test_analysis.py -v
```

## Code Style

Run linting with:
```bash
flake8 analysis.py --max-line-length=120
```

## Key Gotchas

- Session state keys are namespaced per-section to avoid collisions (RFM section uses `_r`, `_f`, `_m` suffixes)
- Monetary values use `Decimal` with `ROUND_HALF_UP` for precision
- Database writes use batch operations via temporary tables to avoid Supabase timeouts
- Cohort recalculation only runs when parameters change to optimize performance
- Cached data loading with 1-hour TTL for improved responsiveness

## Deployment

Push directly to the `main` branch. Use tags for releases (e.g., `v2.0.4`).

## License

[Specify your license here]

## Contact

[Your contact information]