"""Tests for data_loader.py — file ops, DB ops with SQLite mock."""
import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

import data_loader


# ── Path helpers ────────────────────────────────────────────────────────

class TestFilePaths:
    def test_get_excel_file_path_templates(self):
        path = data_loader.get_excel_file_path("sales_template.xlsx")
        assert path == os.path.join("data", "templates_data", "sales_template.xlsx")

    def test_get_excel_file_path_custom(self):
        path = data_loader.get_excel_file_path("foo.xlsx", "download_data")
        assert path == os.path.join("data", "download_data", "foo.xlsx")

    def test_get_download_data_path(self):
        path = data_loader.get_download_data_path("bar.xlsx")
        assert path == os.path.join("data", "download_data", "bar.xlsx")


# ── clear_download_data_folder ──────────────────────────────────────────

class TestClearDownloadFolder:
    def test_creates_folder_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            dl_path = os.path.join(tmp, "download_data")
            with patch("data_loader.os.makedirs") as mock_mkdir, \
                 patch("data_loader.os.listdir", return_value=[]), \
                 patch("data_loader.os.path.isfile", return_value=False):
                data_loader.clear_download_data_folder()
                mock_mkdir.assert_called()

    def test_removes_existing_files(self):
        with patch("data_loader.os.listdir", return_value=["a.xlsx", "b.xlsx"]), \
             patch("data_loader.os.path.isfile", return_value=True), \
             patch("data_loader.os.remove") as mock_rm:
            data_loader.clear_download_data_folder()
            assert mock_rm.call_count == 2


# ── get_current_data_source ────────────────────────────────────────────

class TestGetCurrentDataSource:
    def test_default_when_no_download_folder(self):
        with patch("data_loader.os.path.exists", return_value=False):
            result = data_loader.get_current_data_source()
            assert result == {"sales": "default", "promotion_costs": "default",
                              "other_marketing_costs": "default"}

    def test_detects_custom_files(self):
        with patch("data_loader.os.path.exists", return_value=True), \
             patch("data_loader.os.listdir", return_value=[
                 "sales_template.xlsx", "promotion_costs_template.xlsx"]):
            result = data_loader.get_current_data_source()
            assert result["sales"] == "custom"
            assert result["promotion_costs"] == "custom"
            assert result["other_marketing_costs"] == "default"


# ── get_database_url ───────────────────────────────────────────────────

class TestGetDatabaseUrl:
    def test_secrets_priority(self):
        mock_secrets = MagicMock()
        mock_secrets.get.return_value = "postgresql://from:secrets@db/db"
        with patch("data_loader.st.secrets", mock_secrets), \
             patch("data_loader.os.environ.get", return_value="postgresql://from:env@db/db"):
            assert data_loader.get_database_url() == "postgresql://from:secrets@db/db"

    def test_env_fallback(self):
        mock_secrets = MagicMock()
        mock_secrets.get.side_effect = Exception("no secrets")
        with patch("data_loader.st.secrets", mock_secrets), \
             patch("data_loader.os.environ.get", return_value="postgresql://from:env@db/db"):
            assert data_loader.get_database_url() == "postgresql://from:env@db/db"


# ── check_tables_exist (mocked) ────────────────────────────────────────

class TestCheckTablesExist:
    def test_tables_exist(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalar.side_effect = [True, True]
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        with patch("data_loader.get_engine", return_value=mock_engine):
            assert data_loader.check_tables_exist() is True

    def test_tables_missing(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalar.side_effect = [True, False]
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        with patch("data_loader.get_engine", return_value=mock_engine):
            assert data_loader.check_tables_exist() is False

    def test_connection_error(self):
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("connection failed")
        with patch("data_loader.get_engine", return_value=mock_engine):
            assert data_loader.check_tables_exist() is False


# ── DB helpers (SQLite mock) ───────────────────────────────────────────

@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


class TestSalesTableCreateInsert:
    def test_create_and_insert(self, sqlite_engine):
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            data_loader.create_sales_table()
            df = pd.DataFrame({
                "purchase_date": pd.to_datetime(["2024-01-15"]),
                "order_id": [1],
                "order_price": [100.50],
                "cost": [40.00],
                "client_id": [42],
                "acquisition_channel": ["Google"],
                "cohort": ["Cohort 1"],
            })
            df.to_sql("sales", sqlite_engine, if_exists="append", index=False)
            loaded = pd.read_sql("SELECT * FROM sales", sqlite_engine)
            assert len(loaded) == 1
            assert loaded.iloc[0]["client_id"] == 42

    def test_truncate_preserves_schema(self, sqlite_engine):
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            data_loader.create_sales_table()
            df = pd.DataFrame({
                "purchase_date": pd.to_datetime(["2024-01-15"]),
                "order_id": [1],
                "order_price": [100.50],
                "cost": [40.00],
                "client_id": [42],
                "acquisition_channel": ["Google"],
                "cohort": ["Cohort 1"],
            })
            df.to_sql("sales", sqlite_engine, if_exists="append", index=False)
            with sqlite_engine.begin() as conn:
                conn.execute(text("DELETE FROM sales"))
            assert pd.read_sql("SELECT * FROM sales", sqlite_engine).empty


class TestClientsTable:
    def test_create_and_save_clients(self, sqlite_engine):
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            data_loader.create_clients_table()
            df = pd.DataFrame({
                "client_id": [1, 2],
                "num_orders": [5, 3],
                "first_order_date": pd.to_datetime(["2024-01-10", "2024-02-20"]),
                "last_order_date": pd.to_datetime(["2024-06-15", "2024-07-01"]),
                "total_amount": [500.00, 300.00],
                "first_order_id": [100, 200],
                "first_order_channel": ["Google", "Facebook"],
                "cohort": ["Cohort 1", "Cohort 1"],
            })
            data_loader.save_clients_data(df)
            # Use pd.read_sql directly; load_clients_from_db uses
            # PostgreSQL-specific information_schema queries
            loaded = pd.read_sql("SELECT * FROM clients", sqlite_engine)
            assert len(loaded) == 2
            assert loaded.iloc[0]["client_id"] == 1

    def test_save_preserves_segment_columns(self, sqlite_engine):
        """Segment columns added by ALTER TABLE survive save_clients_data."""
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            data_loader.create_clients_table()
            with sqlite_engine.begin() as conn:
                conn.execute(text("ALTER TABLE clients ADD COLUMN Recency_Segment INTEGER"))

            df = pd.DataFrame({
                "client_id": [1],
                "num_orders": [3],
                "first_order_date": pd.to_datetime(["2024-01-10"]),
                "last_order_date": pd.to_datetime(["2024-06-15"]),
                "total_amount": [300.00],
                "first_order_id": [100],
                "first_order_channel": ["Google"],
                "cohort": ["Cohort 1"],
            })
            data_loader.save_clients_data(df)
            loaded = pd.read_sql("SELECT * FROM clients", sqlite_engine)
            assert "Recency_Segment" in loaded.columns
            assert loaded.iloc[0]["Recency_Segment"] is None


class TestPromotionCostsTable:
    def test_create_and_load(self, sqlite_engine):
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            data_loader.create_promotion_costs_table()
            with sqlite_engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO promotion_costs (channels, expenses_date, costs, cohort)
                    VALUES ('Google', '2024-03-01', 1000.00, 'Cohort 1')
                """))
            df = pd.read_sql("SELECT * FROM promotion_costs", sqlite_engine)
            assert len(df) == 1
            assert df.iloc[0]["channels"] == "Google"


class TestOtherMarketingCostsTable:
    def test_create_and_load(self, sqlite_engine):
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            data_loader.create_other_marketing_costs_table()
            with sqlite_engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO other_marketing_costs (channels, expenses_date, costs, cohort)
                    VALUES ('Email', '2024-03-01', 500.00, 'Cohort 1')
                """))
            df = pd.read_sql("SELECT * FROM other_marketing_costs", sqlite_engine)
            assert len(df) == 1
            assert df.iloc[0]["channels"] == "Email"


class TestCohortsTable:
    def test_create_and_load(self, sqlite_engine):
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            data_loader.create_cohorts_table()
            with sqlite_engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO cohorts (cohort, date_start, date_end)
                    VALUES ('Cohort 1', '2024-01-01', '2024-03-31')
                """))
            df = pd.read_sql("SELECT * FROM cohorts ORDER BY date_start", sqlite_engine)
            assert len(df) == 1
            assert df.iloc[0]["cohort"] == "Cohort 1"


# ── check_database_connection ──────────────────────────────────────────

class TestCheckDatabaseConnection:
    def test_success(self, sqlite_engine):
        with patch("data_loader.get_engine", return_value=sqlite_engine):
            assert data_loader.check_database_connection() is True
