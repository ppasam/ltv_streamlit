"""Data loading module for LTV analysis application."""
import os
from datetime import datetime, timedelta
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

    add_cohort_to_sales()
    populate_clients_from_sales()
    add_cohort_to_expenses_tables()


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


@st.cache_data(ttl=3600, show_spinner=False)
def load_sales_from_db(start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> pd.DataFrame:
    """Load sales data from database with optional date filtering."""
    db_url = get_database_url()

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sales')")
    table_exists = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    if not table_exists:
        create_clients_table()
        create_cohorts_table()
        load_sales_data_to_db(source="templates_data")
        populate_clients_from_sales()
        populate_cohorts_table()

    query = "SELECT purchase_date, order_id, order_price, cost, client_id, acquisition_channel, cohort FROM sales"
    if start_date and end_date:
        query += f" WHERE purchase_date >= '{start_date.strftime('%Y-%m-%d')}' AND purchase_date <= '{end_date.strftime('%Y-%m-%d')}'"

    conn = psycopg2.connect(db_url)
    raw_df = pd.read_sql(query, conn)
    conn.close()

    df = raw_df.rename(columns={
        "purchase_date": "Date",
        "client_id": "Customer ID",
        "order_price": "Revenue"
    })
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])

    return df


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
    db_url = get_database_url()
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS clients"))
        conn.commit()
    
    df = pd.read_excel(uploaded_file)
    df.to_excel(get_download_data_path("sales_template.xlsx"), index=False)
    load_sales_data_to_db(clear=True, source="download_data")
    populate_clients_from_sales()


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


def create_clients_table() -> None:
    """Create clients table in PostgreSQL."""
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            client_id BIGINT PRIMARY KEY,
            num_orders INTEGER,
            first_order_date DATE,
            last_order_date DATE,
            total_amount NUMERIC,
            first_order_id BIGINT,
            first_order_channel VARCHAR,
            cohort VARCHAR
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def add_cohort_to_sales() -> None:
    """Add cohort column to sales table if not exists and populate it."""
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'sales' AND column_name = 'cohort'
    """)
    exists = cur.fetchone()
    
    if not exists:
        cur.execute("ALTER TABLE sales ADD COLUMN cohort VARCHAR")
        conn.commit()
    
    cur.close()
    
    cur.close()
    conn.close()
    
    clients_df = load_clients_from_db()
    if clients_df.empty:
        return
    
    client_cohorts = clients_df.set_index("client_id")["cohort"].to_dict()
    
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    for client_id, cohort in client_cohorts.items():
        if cohort is None:
            cohort = ""
        cur.execute("UPDATE sales SET cohort = %s WHERE client_id = %s", (cohort, client_id))
    
    conn.commit()
    cur.close()
    conn.close()


def add_cohort_to_expenses_tables() -> None:
    """Add cohort column to promotion_costs and other_marketing_costs tables."""
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    tables = ["promotion_costs", "other_marketing_costs"]
    
    for table in tables:
        cur.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table}' AND column_name = 'cohort'
        """)
        exists = cur.fetchone()
        
        if not exists:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN cohort VARCHAR")
    
    conn.commit()
    
    cohorts_df = load_cohorts_from_db()
    if cohorts_df.empty:
        return
    
    for table in tables:
        cur.execute(f"SELECT channels, expenses_date, costs FROM {table}")
        rows = cur.fetchall()
        
        for row in rows:
            channels, expenses_date, _ = row
            if not expenses_date:
                continue
            
            cohort_match = ""
            for _, coh_row in cohorts_df.iterrows():
                date_start = coh_row["date_start"]
                date_end = coh_row["date_end"]
                if isinstance(date_start, str):
                    date_start = datetime.strptime(date_start, '%Y-%m-%d').date()
                if isinstance(date_end, str):
                    date_end = datetime.strptime(date_end, '%Y-%m-%d').date()
                if isinstance(expenses_date, str):
                    expenses_date_dt = datetime.strptime(expenses_date, '%Y-%m-%d').date()
                else:
                    expenses_date_dt = expenses_date
                
                if date_start <= expenses_date_dt <= date_end:
                    cohort_match = coh_row["cohort"]
                    break
            
            cur.execute(f"UPDATE {table} SET cohort = %s WHERE channels = %s AND expenses_date = %s", 
                       (cohort_match, channels, expenses_date))
    
    conn.commit()
    cur.close()
    conn.close()


def save_clients_data(df: pd.DataFrame) -> None:
    """Save clients data to PostgreSQL."""
    create_clients_table()
    db_url = get_database_url()
    engine = create_engine(db_url)
    df.to_sql("clients", engine, if_exists="replace", index=False)


@st.cache_data(ttl=3600, show_spinner=False)
def load_clients_from_db() -> pd.DataFrame:
    """Load clients data from PostgreSQL."""
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'clients')")
    table_exists = cur.fetchone()[0]
    conn.close()
    
    if not table_exists:
        return pd.DataFrame()
    
    df = pd.read_sql("SELECT * FROM clients", db_url)
    return df


def populate_clients_from_sales() -> None:
    """Populate clients table with unique customer IDs from sales."""
    sales_df = load_sales_from_db()
    
    if sales_df.empty or "Customer ID" not in sales_df.columns:
        return
    
    import cohorts as coh
    
    sales_df_copy = sales_df.copy()
    if "order_id" not in sales_df_copy.columns:
        sales_df_copy["order_id"] = range(1, len(sales_df_copy) + 1)
    
    client_stats = sales_df_copy.groupby("Customer ID").agg(
        num_orders=("Customer ID", "count"),
        first_order_date=("Date", "min"),
        last_order_date=("Date", "max"),
        total_amount=("Revenue", "sum")
    ).reset_index()
    
    first_orders = sales_df_copy.sort_values(["Date", "order_id"]).groupby("Customer ID").first().reset_index()
    first_orders = first_orders[["Customer ID", "order_id", "acquisition_channel"]]
    first_orders = first_orders.rename(columns={"order_id": "first_order_id"})
    
    client_data = client_stats.merge(first_orders, on="Customer ID", how="left")
    client_data = client_data.rename(columns={
        "Customer ID": "client_id",
        "acquisition_channel": "first_order_channel"
    })
    
    client_data["first_order_date"] = pd.to_datetime(client_data["first_order_date"]).dt.strftime('%Y-%m-%d')
    client_data["last_order_date"] = pd.to_datetime(client_data["last_order_date"]).dt.strftime('%Y-%m-%d')
    
    min_date = sales_df["Date"].min()
    max_date = sales_df["Date"].max()
    num_cohorts = 8
    _, cohort_dates = coh.recalculate_from_num_cohorts(
        start_date=min_date,
        end_date=max_date,
        cohort_type=coh.COHORT_TYPE_MONTHS,
        num_cohorts=num_cohorts
    )
    
    def get_cohort(date_str):
        if pd.isna(date_str):
            return ""
        date = pd.to_datetime(date_str)
        for i, cohort_date in enumerate(cohort_dates):
            if i < len(cohort_dates) - 1:
                if cohort_date <= date < cohort_dates[i + 1]:
                    return f"Cohort {i + 1}"
            else:
                return f"Cohort {i + 1}"
        return ""
    
    client_data["cohort"] = client_data["first_order_date"].apply(get_cohort)
    
    save_clients_data(client_data)
    add_cohort_to_sales()
    populate_cohorts_table()
    add_cohort_to_expenses_tables()


def create_cohorts_table() -> None:
    """Create cohorts table in PostgreSQL."""
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cohorts (
            cohort VARCHAR PRIMARY KEY,
            date_start DATE,
            date_end DATE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def update_cohorts_in_db(start_date: datetime, end_date: datetime,
                          cohort_type: str, cohort_size: int,
                          num_cohorts: int) -> None:
    """Update cohorts table in PostgreSQL based on parameters."""
    import cohorts as coh

    if cohort_type == coh.COHORT_TYPE_DAYS:
        _, cohort_dates = coh.recalculate_from_cohort_size(
            start_date=start_date,
            end_date=end_date,
            cohort_type=cohort_type,
            cohort_size=cohort_size
        )
    else:
        _, cohort_dates = coh.recalculate_from_num_cohorts(
            start_date=start_date,
            end_date=end_date,
            cohort_type=cohort_type,
            num_cohorts=num_cohorts
        )

    cohorts_data = []
    for i, cs in enumerate(cohort_dates):
        if i < len(cohort_dates) - 1:
            ce = cohort_dates[i + 1] - timedelta(days=1)
        else:
            ce = end_date
        if ce > end_date:
            ce = end_date
        cohorts_data.append({
            "cohort": f"Cohort {i + 1}",
            "date_start": cs.strftime('%Y-%m-%d'),
            "date_end": ce.strftime('%Y-%m-%d')
        })

    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("DELETE FROM cohorts")
    conn.commit()

    for row in cohorts_data:
        cur.execute(
            "INSERT INTO cohorts (cohort, date_start, date_end) VALUES (%s, %s, %s)",
            (row["cohort"], row["date_start"], row["date_end"])
        )

    conn.commit()
    cur.close()
    conn.close()


def populate_cohorts_table() -> None:
    """Populate cohorts table based on cohort calculations."""
    import cohorts as coh
    
    sales_df = load_sales_from_db()
    if sales_df.empty:
        return
    
    min_date = sales_df["Date"].min()
    max_date = sales_df["Date"].max()
    
    num_cohorts = 8
    _, cohort_dates = coh.recalculate_from_num_cohorts(
        start_date=min_date,
        end_date=max_date,
        cohort_type=coh.COHORT_TYPE_MONTHS,
        num_cohorts=num_cohorts
    )
    
    cohorts_data = []
    for i, start_date in enumerate(cohort_dates):
        if i < len(cohort_dates) - 1:
            end_date = cohort_dates[i + 1] - timedelta(days=1)
        else:
            end_date = max_date
        cohorts_data.append({
            "cohort": f"Cohort {i + 1}",
            "date_start": start_date.strftime('%Y-%m-%d'),
            "date_end": end_date.strftime('%Y-%m-%d')
        })
    
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("DELETE FROM cohorts")
    conn.commit()
    
    for row in cohorts_data:
        cur.execute(
            "INSERT INTO cohorts (cohort, date_start, date_end) VALUES (%s, %s, %s)",
            (row["cohort"], row["date_start"], row["date_end"])
        )
    
    conn.commit()
    cur.close()
    conn.close()


@st.cache_data(ttl=3600, show_spinner=False)
def load_cohorts_from_db() -> pd.DataFrame:
    """Load cohorts data from PostgreSQL."""
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'cohorts')")
    table_exists = cur.fetchone()[0]
    conn.close()
    
    if not table_exists:
        return pd.DataFrame()
    
    df = pd.read_sql("SELECT * FROM cohorts ORDER BY date_start", db_url)
    return df