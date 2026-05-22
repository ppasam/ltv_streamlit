"""Data loading module for LTV analysis application."""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import Date, Numeric, create_engine, text


def get_database_url() -> str:
    """Get database URL from Streamlit secrets, environment, or use default."""
    try:
        return st.secrets.get(
            "DATABASE_URL",
            os.environ.get("DATABASE_URL", "postgresql://ltv_user:ltv_pass@localhost:5432/ltv_db")
        )
    except Exception:
        return os.environ.get(
            "DATABASE_URL",
            "postgresql://ltv_user:ltv_pass@localhost:5432/ltv_db"
        )


@st.cache_resource
def get_engine():
    """Get cached SQLAlchemy engine for database access."""
    return create_engine(get_database_url())


def get_excel_file_path(filename: str, subfolder: str = "templates_data") -> str:
    """Get full path to Excel file in data directory."""
    return os.path.join("data", subfolder, filename)


def get_download_data_path(filename: str) -> str:
    """Get path to download_data folder."""
    return os.path.join("data", "download_data", filename)


def clear_download_data_folder() -> None:
    """Clear all files in download_data folder."""
    download_path = os.path.join("data", "download_data")
    os.makedirs(download_path, exist_ok=True)
    for file in os.listdir(download_path):
        file_path = os.path.join(download_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)


def check_tables_exist() -> bool:
    """Check if required database tables exist and have data."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sales')")
            )
            sales_exists = result.scalar()
            result = conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'clients')")
            )
            clients_exists = result.scalar()
        return bool(sales_exists and clients_exists)
    except Exception:
        return False


def migrate_database_schema() -> None:
    """Migrate existing tables to proper column types (DATE, NUMERIC, etc)."""
    engine = get_engine()
    migrations = [
        "ALTER TABLE clients ALTER COLUMN first_order_date TYPE DATE USING first_order_date::date",
        "ALTER TABLE clients ALTER COLUMN last_order_date TYPE DATE USING last_order_date::date",
        "ALTER TABLE clients ALTER COLUMN total_amount TYPE NUMERIC(12,2) USING total_amount::numeric",
        "ALTER TABLE sales ALTER COLUMN order_price TYPE NUMERIC(10,2) USING order_price::numeric",
        "ALTER TABLE sales ALTER COLUMN cost TYPE NUMERIC(10,2) USING cost::numeric",
        "ALTER TABLE promotion_costs ALTER COLUMN costs TYPE NUMERIC(10,2) USING costs::numeric",
        "ALTER TABLE other_marketing_costs ALTER COLUMN costs TYPE NUMERIC(10,2) USING costs::numeric",
    ]
    for sql in migrations:
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
        except Exception:
            pass

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_sales_client_id ON sales(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_sales_cohort ON sales(cohort)",
        "CREATE INDEX IF NOT EXISTS idx_sales_purchase_date ON sales(purchase_date)",
        "CREATE INDEX IF NOT EXISTS idx_clients_cohort ON clients(cohort)",
        "CREATE INDEX IF NOT EXISTS idx_clients_first_order_date ON clients(first_order_date)",
        "CREATE INDEX IF NOT EXISTS idx_clients_last_order_date ON clients(last_order_date)",
        "CREATE INDEX IF NOT EXISTS idx_promotion_costs_cohort ON promotion_costs(cohort)",
        "CREATE INDEX IF NOT EXISTS idx_other_marketing_costs_cohort ON other_marketing_costs(cohort)",
    ]
    for sql in indexes:
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
        except Exception:
            pass


def get_current_data_source() -> dict:
    """Check which data source is currently loaded in PostgreSQL."""
    download_path = os.path.join("data", "download_data")

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


def create_sales_table() -> None:
    """Create sales table with proper schema if not exists."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sales (
                purchase_date DATE NOT NULL,
                order_id BIGINT,
                order_price NUMERIC(10,2) NOT NULL,
                cost NUMERIC(10,2),
                client_id BIGINT NOT NULL,
                acquisition_channel VARCHAR(255),
                cohort VARCHAR(50)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sales_client_id ON sales(client_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sales_cohort ON sales(cohort)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sales_purchase_date ON sales(purchase_date)
        """))


def create_promotion_costs_table() -> None:
    """Create promotion_costs table with proper schema if not exists."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS promotion_costs (
                channels VARCHAR(255),
                expenses_date DATE,
                costs NUMERIC(10,2),
                cohort VARCHAR(50)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_promotion_costs_cohort ON promotion_costs(cohort)
        """))


def create_other_marketing_costs_table() -> None:
    """Create other_marketing_costs table with proper schema if not exists."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS other_marketing_costs (
                channels VARCHAR(255),
                expenses_date DATE,
                costs NUMERIC(10,2),
                cohort VARCHAR(50)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_other_marketing_costs_cohort ON other_marketing_costs(cohort)
        """))


def create_clients_table() -> None:
    """Create clients table with proper schema if not exists."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS clients (
                client_id BIGINT PRIMARY KEY,
                num_orders INTEGER,
                first_order_date DATE,
                last_order_date DATE,
                total_amount NUMERIC(12,2),
                first_order_id BIGINT,
                first_order_channel VARCHAR(255),
                cohort VARCHAR(50)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_clients_cohort ON clients(cohort)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_clients_first_order_date ON clients(first_order_date)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_clients_last_order_date ON clients(last_order_date)
        """))


def create_cohorts_table() -> None:
    """Create cohorts table with proper schema if not exists."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cohorts (
                cohort VARCHAR(50) PRIMARY KEY,
                date_start DATE NOT NULL,
                date_end DATE NOT NULL
            )
        """))


_SALES_DTYPE = {
    "purchase_date": Date(),
    "order_price": Numeric(10, 2),
    "cost": Numeric(10, 2),
}
_COSTS_DTYPE = {
    "expenses_date": Date(),
    "costs": Numeric(10, 2),
}
_CLIENTS_DTYPE = {
    "first_order_date": Date(),
    "last_order_date": Date(),
    "total_amount": Numeric(12, 2),
}
_COHORTS_DTYPE = {
    "date_start": Date(),
    "date_end": Date(),
}


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

    populate_clients_from_sales()
    try:
        start_date, end_date = get_sales_date_range()
        import cohorts as coh
        update_cohorts_in_db(
            start_date=start_date,
            end_date=end_date,
            cohort_type=coh.COHORT_TYPE_MONTHS,
            cohort_size=3,
            num_cohorts=8,
            calculation_mode="Cohort Size"
        )
    except Exception:
        pass


@st.cache_data(ttl=3600, show_spinner=False)
def load_sales_from_db(start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> pd.DataFrame:
    """Load sales data from database with optional date filtering."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sales')")
        )
        table_exists = result.scalar()

    if not table_exists:
        create_clients_table()
        create_cohorts_table()
        load_sales_data_to_db(source="templates_data")
        populate_clients_from_sales()

    if start_date and end_date:
        sd = start_date.strftime('%Y-%m-%d')
        ed = end_date.strftime('%Y-%m-%d')
        raw_df = pd.read_sql(
            f"""
                SELECT purchase_date, order_id, order_price, cost,
                       client_id, acquisition_channel, cohort
                FROM sales
                WHERE purchase_date >= '{sd}' AND purchase_date <= '{ed}'
            """,
            engine
        )
    else:
        raw_df = pd.read_sql(
            "SELECT purchase_date, order_id, order_price, cost, client_id, acquisition_channel, cohort FROM sales",
            engine
        )

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


@st.cache_data(ttl=3600, show_spinner=False)
def get_sales_date_range() -> Tuple[datetime, datetime]:
    """Get the min and max dates from sales data."""
    try:
        engine = get_engine()
        result_df = pd.read_sql(
            "SELECT MIN(purchase_date) as min_date, MAX(purchase_date) as max_date FROM sales",
            engine
        )
        if not result_df.empty:
            min_date = result_df["min_date"].iloc[0]
            max_date = result_df["max_date"].iloc[0]
        if isinstance(min_date, str):
            min_date = datetime.strptime(min_date.split(' ')[0], '%Y-%m-%d')
        if isinstance(max_date, str):
            max_date = datetime.strptime(max_date.split(' ')[0], '%Y-%m-%d')
        # Ensure we return datetime.datetime objects
        if hasattr(min_date, 'date') and not hasattr(min_date, 'hour'):
            # It's a date object, convert to datetime
            min_date = datetime.combine(min_date, datetime.min.time())
        if hasattr(max_date, 'date') and not hasattr(max_date, 'hour'):
            # It's a date object, convert to datetime
            max_date = datetime.combine(max_date, datetime.min.time())
        return min_date, max_date
    except Exception:
        pass

    df = load_sales_data()
    if "Date" in df.columns:
        min_date = df["Date"].min()
        max_date = df["Date"].max()
        # Convert to datetime.datetime if needed
        if hasattr(min_date, 'date') and not hasattr(min_date, 'hour'):
            # It's a date object, convert to datetime
            min_date = datetime.combine(min_date, datetime.min.time())
        if hasattr(max_date, 'date') and not hasattr(max_date, 'hour'):
            # It's a date object, convert to datetime
            max_date = datetime.combine(max_date, datetime.min.time())
        return min_date, max_date
    return datetime(2024, 1, 1), datetime(2025, 12, 31)


def check_database_connection() -> bool:
    """Check if database connection is available."""
    try:
        with get_engine().connect():
            pass
        return True
    except Exception:
        return False


def load_sales_data_to_db(clear: bool = False, source: str = "templates_data") -> None:
    """Load sales data to database preserving schema."""
    engine = get_engine()
    create_sales_table()

    if clear:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE sales"))

    df = pd.read_excel(get_excel_file_path("sales_template.xlsx", source))
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    df.to_sql("sales", engine, if_exists="append", index=False, dtype=_SALES_DTYPE)


def load_promotion_costs_to_db(clear: bool = False, source: str = "templates_data") -> None:
    """Load promotion costs data to database preserving schema."""
    engine = get_engine()
    create_promotion_costs_table()

    if clear:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE promotion_costs"))

    df = pd.read_excel(get_excel_file_path("promotion_costs_template.xlsx", source))
    df["expenses_date"] = pd.to_datetime(df["expenses_date"])
    df.to_sql("promotion_costs", engine, if_exists="append", index=False, dtype=_COSTS_DTYPE)


def load_other_marketing_costs_to_db(clear: bool = False, source: str = "templates_data") -> None:
    """Load other marketing costs data to database preserving schema."""
    engine = get_engine()
    create_other_marketing_costs_table()

    if clear:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE other_marketing_costs"))

    df = pd.read_excel(get_excel_file_path("other_marketing_costs_template.xlsx", source))
    df["expenses_date"] = pd.to_datetime(df["expenses_date"])
    df.to_sql("other_marketing_costs", engine, if_exists="append", index=False, dtype=_COSTS_DTYPE)


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
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS clients"))

    df = pd.read_excel(uploaded_file)
    df.to_excel(get_download_data_path("sales_template.xlsx"), index=False)
    load_sales_data_to_db(clear=True, source="download_data")
    populate_clients_from_sales()
    try:
        start_date, end_date = get_sales_date_range()
        import cohorts as coh
        update_cohorts_in_db(
            start_date=start_date,
            end_date=end_date,
            cohort_type=coh.COHORT_TYPE_MONTHS,
            cohort_size=3,
            num_cohorts=8,
            calculation_mode="Cohort Size"
        )
    except Exception:
        pass
    st.cache_data.clear()
    st.session_state._cohort_params = None


def load_custom_promotion_costs_to_db(uploaded_file) -> None:
    """Load custom promotion costs data to database."""
    df = pd.read_excel(uploaded_file)
    df.to_excel(get_download_data_path("promotion_costs_template.xlsx"), index=False)
    load_promotion_costs_to_db(clear=True, source="download_data")
    st.cache_data.clear()


def load_custom_other_marketing_costs_to_db(uploaded_file) -> None:
    """Load custom other marketing costs data to database."""
    df = pd.read_excel(uploaded_file)
    df.to_excel(get_download_data_path("other_marketing_costs_template.xlsx"), index=False)
    load_other_marketing_costs_to_db(clear=True, source="download_data")
    st.cache_data.clear()


@st.cache_data(ttl=3600, show_spinner=False)
def load_promotion_costs_from_db() -> pd.DataFrame:
    """Load promotion costs data from PostgreSQL database."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'promotion_costs')")
            )
            table_exists = result.scalar()

        if not table_exists:
            return load_promotion_costs_data()

        return pd.read_sql("SELECT * FROM promotion_costs", engine)
    except Exception:
        return load_promotion_costs_data()


@st.cache_data(ttl=3600, show_spinner=False)
def load_other_marketing_costs_from_db() -> pd.DataFrame:
    """Load other marketing costs data from PostgreSQL database."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'other_marketing_costs')")
            )
            table_exists = result.scalar()

        if not table_exists:
            return load_other_marketing_costs_data()

        return pd.read_sql("SELECT * FROM other_marketing_costs", engine)
    except Exception:
        return load_other_marketing_costs_data()


def add_cohort_to_sales() -> None:
    """Add cohort column to sales table if not exists and populate it."""
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS cohort VARCHAR(50)"))

    clients_df = load_clients_from_db()
    if clients_df.empty:
        return

    cohort_map = clients_df[["client_id", "cohort"]].copy()
    cohort_map["cohort"] = cohort_map["cohort"].fillna("")
    cohort_map.to_sql("_tmp_sales_cohorts", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE sales s
            SET cohort = t.cohort
            FROM _tmp_sales_cohorts t
            WHERE s.client_id = t.client_id
        """))
        conn.execute(text("DROP TABLE IF EXISTS _tmp_sales_cohorts"))


def add_cohort_to_expenses_tables() -> None:
    """Add cohort column to promotion_costs and other_marketing_costs tables."""
    engine = get_engine()

    tables = ["promotion_costs", "other_marketing_costs"]

    for table in tables:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS cohort VARCHAR(50)"))

    cohorts_df = load_cohorts_from_db()
    if cohorts_df.empty:
        return

    cohorts_df = cohorts_df.copy()
    cohorts_df["date_start"] = pd.to_datetime(cohorts_df["date_start"])
    cohorts_df["date_end"] = pd.to_datetime(cohorts_df["date_end"])

    for table in tables:
        df = pd.read_sql(f"SELECT * FROM {table}", engine)
        if df.empty:
            continue

        def assign_cohort(expenses_date):
            if pd.isna(expenses_date):
                return ""
            ed = pd.to_datetime(expenses_date)
            mask = (cohorts_df["date_start"] <= ed) & (ed <= cohorts_df["date_end"])
            matching = cohorts_df[mask]
            return matching.iloc[0]["cohort"] if not matching.empty else ""

        df["cohort"] = df["expenses_date"].apply(assign_cohort)
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        df.to_sql(table, engine, if_exists="append", index=False, dtype=_COSTS_DTYPE)


def save_clients_data(df: pd.DataFrame) -> None:
    """Save clients data to PostgreSQL, preserving schema."""
    create_clients_table()
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM clients"))
    df.to_sql("clients", engine, if_exists="append", index=False, dtype=_CLIENTS_DTYPE)


@st.cache_data(ttl=3600, show_spinner=False)
def load_clients_from_db() -> pd.DataFrame:
    """Load clients data from PostgreSQL."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'clients')")
        )
        table_exists = result.scalar()

    if not table_exists:
        return pd.DataFrame()

    return pd.read_sql("SELECT * FROM clients", engine)


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

    # Keep as datetime — downstream code handles both str and datetime
    client_data["first_order_date"] = pd.to_datetime(client_data["first_order_date"])
    client_data["last_order_date"] = pd.to_datetime(client_data["last_order_date"])

    min_date = sales_df["Date"].min()
    max_date = sales_df["Date"].max()
    num_cohorts = 8
    _, cohort_dates = coh.recalculate_from_num_cohorts(
        start_date=min_date,
        end_date=max_date,
        cohort_type=coh.COHORT_TYPE_MONTHS,
        num_cohorts=num_cohorts
    )

    def get_cohort(date):
        if pd.isna(date):
            return ""
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
    add_cohort_to_expenses_tables()


def update_cohorts_in_db(start_date: datetime, end_date: datetime,
                          cohort_type: str, cohort_size: int,
                          num_cohorts: int, calculation_mode: str = "Cohort Size") -> None:
    """Update cohorts table in PostgreSQL based on parameters."""
    import cohorts as coh

    if calculation_mode == "Cohort Size":
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
            "date_start": cs,
            "date_end": ce
        })

    engine = get_engine()
    create_cohorts_table()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM cohorts"))

    cohorts_df = pd.DataFrame(cohorts_data)
    cohorts_df.to_sql("cohorts", engine, if_exists="append", index=False, dtype=_COHORTS_DTYPE)


@st.cache_data(ttl=3600, show_spinner=False)
def load_cohorts_from_db() -> pd.DataFrame:
    """Load cohorts data from PostgreSQL."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'cohorts')")
        )
        table_exists = result.scalar()

    if not table_exists:
        return pd.DataFrame()

    df = pd.read_sql("SELECT * FROM cohorts ORDER BY date_start", engine)
    if not df.empty:
        for col in ["date_start", "date_end"]:
            if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col])
    return df
