"""Main Streamlit application for LTV analysis."""
import os
from datetime import datetime

import streamlit as st

import cohorts
import data_loader
import ui


st.set_page_config(page_title="LTV", layout="wide")

st.title("LTV")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ltv_user:ltv_pass@localhost:5432/ltv_db"
)

if "initialized" not in st.session_state:
    st.session_state.initialized = False
    data_loader.init_database_from_templates()
    st.session_state.initialized = True

if "cohort_size_input" not in st.session_state:
    st.session_state.cohort_size_input = 3
if "num_cohorts_input" not in st.session_state:
    st.session_state.num_cohorts_input = 8
if "cohort_dates_input" not in st.session_state:
    st.session_state.cohort_dates_input = []
if "prev_cohort_size" not in st.session_state:
    st.session_state.prev_cohort_size = 3
if "prev_num_cohorts" not in st.session_state:
    st.session_state.prev_num_cohorts = 8
if "calculation_mode" not in st.session_state:
    st.session_state.calculation_mode = "Cohort Size"


def get_date_range() -> tuple[datetime, datetime]:
    """Get date range from sales data."""
    try:
        return data_loader.get_sales_date_range()
    except Exception:
        return datetime(2013, 1, 1), datetime(2014, 12, 31)


def main() -> None:
    """Main application function."""
    start_date, end_date = get_date_range()
    
    section, selected_start, selected_end, cohort_type, num_cohorts, cohort_size, cohort_dates, is_days = ui.render_sidebar(start_date, end_date)
    
    ui.render_section(
        section, selected_start, selected_end,
        cohort_dates=cohort_dates,
        num_cohorts=num_cohorts,
        cohort_size=cohort_size,
        is_days=is_days
    )


if __name__ == "__main__":
    main()