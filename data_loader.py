"""Data loading module for LTV analysis application."""
import os
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
import psycopg2
import streamlit as st
from sqlalchemy import create_engine, text


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://ltv_user:ltv_pass@localhost:5432/ltv_db"
    )


def get_excel_file_path(filename: str, subfolder: str = "templates_data") -> str:
    """Get full path to Excel file in data directory."""
    return os.path.join("data", subfolder, filename)


def get_download_data_path(filename: str) -> str:
    """Get path to download_data folder."""
    return os.path.join("data", "download_data", filename)


def clear_download_data_folder() -> None:
    """Clear all files in download_data folder."""
    download_path = os.path.join("data", "download_data")
    if os.path.exists(download_path):
        for file in os.listdir(download_path):
            file_path = os.path.join(download_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)


def get_current_data_source() -> dict:
    """Check which data source is currently loaded in PostgreSQL."""
    download_path = os.path.join("data", "download_data")
    templates_path = os.path.join("data", "templates_data")

    result = {
        "sales": "default",
        "promotion_costs": "default",
        "other_marketing_costs": "default"
    }

    if not os.path.exists(download_path):
        return result

    download_files = os.listdir(download_path)

    if "sales_template.xlsx" in download_files:
        result["sales"] = "custom"
    if "promotion_costs_template.xlsx" in download_files:
        result["promotion_costs"] = "custom"
    if "other_marketing_costs_template.xlsx" in download_files:
        result["other_marketing_costs"] = "custom"

    return result


@st.cache_data(ttl=3600)
def load_sales_data(subfolder: str = "templates_data") -> pd.DataFrame:
    """Load sales data from Excel template with caching."""
    file_path = get_excel_file_path("sales_template.xlsx", subfolder)
    df = pd.read_excel(file_path)
    df = df.rename(columns={
        "purchase_date": "Date",
        "client_id": "Customer ID",
        "order_price": "Revenue"
    })
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@st.cache_data(ttl=3600)
def load_promotion_costs_data(subfolder: str = "templates_data") -> pd.DataFrame:
    """Load promotion costs data from Excel template with caching."""
    file_path = get_excel_file_path("promotion_costs_template.xlsx", subfolder)
    df = pd.read_excel(file_path)
    return df


@st.cache_data(ttl=3600)
def load_other_marketing_costs_data(subfolder: str = "templates_data") -> pd.DataFrame:
    """Load other marketing costs data from Excel template with caching."""
    file_path = get_excel_file_path("other_marketing_costs_template.xlsx", subfolder)
    df = pd.read_excel(file_path)
    return df


def get_date_range_from_db() -> Tuple[datetime, datetime]:
    """Get date range from sales data in database."""
    df = load_sales_data()
    min_date = df["Date"].min()
    max_date = df["Date"].max()
    return min_date, max_date


def init_database_from_templates() -> None:
    """Initialize database with data from templates_data folder."""
    clear_download_data_folder()
    load_sales_data_to_db(clear=True)
    load_promotion_costs_to_db(clear=True)
    load_other_marketing_costs_to_db(clear=True)


def init_database() -> None:
    """Initialize database and load data from Excel templates."""
    db_url = get_database_url()
    engine = create_engine(db_url)

    sales_df = load_sales_data()
    promotion_df = load_promotion_costs_data()
    marketing_df = load_other_marketing_costs_data()

    sales_df.to_sql("sales", engine, if_exists="replace", index=False)
    promotion_df.to_sql("promotion_costs", engine, if_exists="replace", index=False)
    marketing_df.to_sql("other_marketing_costs", engine, if_exists="replace", index=False)


@st.cache_data(ttl=3600)
def load_sales_from_db(start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> pd.DataFrame:
    """Load sales data from database with optional date filtering."""
    db_url = get_database_url()

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sales')")
        table_exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        if not table_exists:
            return _load_sales_from_excel(start_date, end_date)

        query = "SELECT * FROM sales"
        if start_date and end_date:
            query += f" WHERE purchase_date >= '{start_date.strftime('%Y-%m-%d')}' AND purchase_date <= '{end_date.strftime('%Y-%m-%d')}'"

        conn = psycopg2.connect(db_url)
        df = pd.read_sql(query, conn)
        conn.close()

        df = df.rename(columns={
            "purchase_date": "Date",
            "client_id": "Customer ID",
            "order_price": "Revenue"
        })
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])

        return df
    except Exception:
        return _load_sales_from_excel(start_date, end_date)


def _load_sales_from_excel(start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> pd.DataFrame:
    """Load sales data from Excel file with optional date filtering."""
    df = load_sales_data()

    if "Date" in df.columns and start_date and end_date:
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

    return df


@st.cache_data(ttl=3600)
def get_sales_date_range() -> Tuple[datetime, datetime]:
    """Get the min and max dates from sales data."""
    try:
        db_url = get_database_url()
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sales')")
        table_exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        if table_exists:
            conn = psycopg2.connect(db_url)
            query = "SELECT MIN(purchase_date) as min_date, MAX(purchase_date) as max_date FROM sales"
            result = pd.read_sql(query, conn)
            conn.close()
            if not result.empty:
                min_date = result["min_date"].iloc[0]
                max_date = result["max_date"].iloc[0]
                if isinstance(min_date, str):
                    min_date = datetime.strptime(min_date.split(' ')[0], '%Y-%m-%d')
                if isinstance(max_date, str):
                    max_date = datetime.strptime(max_date.split(' ')[0], '%Y-%m-%d')
                return min_date, max_date
    except Exception:
        pass

    df = load_sales_data()
    if "Date" in df.columns:
        min_date = df["Date"].min()
        max_date = df["Date"].max()
        if hasattr(min_date, 'date'):
            return min_date, max_date
        return datetime(2013, 1, 1), datetime(2014, 12, 31)
    return datetime(2013, 1, 1), datetime(2014, 12, 31)


def check_database_connection() -> bool:
    """Check if database connection is available."""
    try:
        db_url = get_database_url()
        conn = psycopg2.connect(db_url)
        conn.close()
        return True
    except Exception:
        return False


def load_sales_data_to_db(clear: bool = False, source: str = "templates_data") -> None:
    """Load sales data to database."""
    db_url = get_database_url()
    engine = create_engine(db_url)

    if clear:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS sales"))
            conn.commit()

    df = pd.read_excel(get_excel_file_path("sales_template.xlsx", source))
    df.to_sql("sales", engine, if_exists="replace", index=False)


def load_promotion_costs_to_db(clear: bool = False, source: str = "templates_data") -> None:
    """Load promotion costs data to database."""
    db_url = get_database_url()
    engine = create_engine(db_url)

    if clear:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS promotion_costs"))
            conn.commit()

    df = pd.read_excel(get_excel_file_path("promotion_costs_template.xlsx", source))
    df.to_sql("promotion_costs", engine, if_exists="replace", index=False)


def load_other_marketing_costs_to_db(clear: bool = False, source: str = "templates_data") -> None:
    """Load other marketing costs data to database."""
    db_url = get_database_url()
    engine = create_engine(db_url)

    if clear:
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS other_marketing_costs"))
            conn.commit()

    df = pd.read_excel(get_excel_file_path("other_marketing_costs_template.xlsx", source))
    df.to_sql("other_marketing_costs", engine, if_exists="replace", index=False)


def save_uploaded_data(uploaded_file) -> None:
    """Save uploaded Excel file to download_data directory and update database."""
    clear_download_data_folder()

    excel_file = pd.ExcelFile(uploaded_file)

    sales_df = pd.read_excel(excel_file, sheet_name="sales")
    promotion_df = pd.read_excel(excel_file, sheet_name="promotion_costs")
    marketing_df = pd.read_excel(excel_file, sheet_name="other_marketing_costs")

    sales_df.to_excel(get_download_data_path("sales_template.xlsx"), index=False)
    promotion_df.to_excel(get_download_data_path("promotion_costs_template.xlsx"), index=False)
    marketing_df.to_excel(get_download_data_path("other_marketing_costs_template.xlsx"), index=False)

    load_sales_data_to_db(clear=True, source="download_data")
    load_promotion_costs_to_db(clear=True, source="download_data")
    load_other_marketing_costs_to_db(clear=True, source="download_data")


def load_custom_sales_to_db(uploaded_file) -> None:
    """Load custom sales data to database."""
    df = pd.read_excel(uploaded_file)
    df.to_excel(get_download_data_path("sales_template.xlsx"), index=False)
    load_sales_data_to_db(clear=True, source="download_data")


def load_custom_promotion_costs_to_db(uploaded_file) -> None:
    """Load custom promotion costs data to database."""
    df = pd.read_excel(uploaded_file)
    df.to_excel(get_download_data_path("promotion_costs_template.xlsx"), index=False)
    load_promotion_costs_to_db(clear=True, source="download_data")


def load_custom_other_marketing_costs_to_db(uploaded_file) -> None:
    """Load custom other marketing costs data to database."""
    df = pd.read_excel(uploaded_file)
    df.to_excel(get_download_data_path("other_marketing_costs_template.xlsx"), index=False)
    load_other_marketing_costs_to_db(clear=True, source="download_data")


@st.cache_data(ttl=3600)
def load_promotion_costs_from_db() -> pd.DataFrame:
    """Load promotion costs data from PostgreSQL database."""
    try:
        db_url = get_database_url()
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'promotion_costs')")
        table_exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        if not table_exists:
            return load_promotion_costs_data()

        conn = psycopg2.connect(db_url)
        df = pd.read_sql("SELECT * FROM promotion_costs", conn)
        conn.close()
        return df
    except Exception:
        return load_promotion_costs_data()


@st.cache_data(ttl=3600)
def load_other_marketing_costs_from_db() -> pd.DataFrame:
    """Load other marketing costs data from PostgreSQL database."""
    try:
        db_url = get_database_url()
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'other_marketing_costs')")
        table_exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        if not table_exists:
            return load_other_marketing_costs_data()

        conn = psycopg2.connect(db_url)
        df = pd.read_sql("SELECT * FROM other_marketing_costs", conn)
        conn.close()
        return df
    except Exception:
        return load_other_marketing_costs_data()