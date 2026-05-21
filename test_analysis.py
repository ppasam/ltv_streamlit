"""Tests for analysis module."""
from decimal import Decimal

import pandas as pd
import pytest
from datetime import datetime

from analysis import (
    calculate_overall_metrics,
    calculate_revenue_table,
    calculate_cost_table,
    calculate_profit_table,
    calculate_orders_table,
    calculate_avg_profit_per_order_table,
    calculate_profit_by_channel_table,
    calculate_orders_by_channel_table,
    calculate_avg_profit_by_channel_table,
    calculate_avg_acquisition_cost_table,
    calculate_promotion_costs_table,
    calculate_other_marketing_costs_table,
    propagate_monetary_values,
)


@pytest.fixture
def sales_df():
    return pd.DataFrame({
        "Date": pd.to_datetime(["2024-01-15", "2024-01-20", "2024-02-10", "2024-02-15"]),
        "Customer ID": ["C1", "C2", "C1", "C3"],
        "Revenue": [100.0, 200.0, 150.0, 300.0],
        "cost": [50.0, 100.0, 75.0, 150.0],
        "acquisition_channel": ["Organic", "Paid", "Organic", "Paid"],
        "cohort": ["C1", "C1", "C1", "C2"],
    })


@pytest.fixture
def cohorts_df():
    return pd.DataFrame({
        "cohort": ["C1", "C2"],
        "date_start": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        "date_end": pd.to_datetime(["2024-01-31", "2024-02-28"]),
    })


@pytest.fixture
def promotion_df():
    return pd.DataFrame({
        "cohort": ["C1", "C2"],
        "channels": ["Organic", "Paid"],
        "costs": [100.0, 200.0],
    })


@pytest.fixture
def marketing_df():
    return pd.DataFrame({
        "cohort": ["C1", "C2"],
        "channels": ["Organic", "Paid"],
        "costs": [50.0, 80.0],
    })


@pytest.fixture
def clients_df():
    return pd.DataFrame({
        "client_id": ["C1", "C2", "C3"],
        "num_orders": [2, 1, 1],
        "total_amount": [250.0, 200.0, 300.0],
        "cohort": ["C1", "C1", "C2"],
    })


@pytest.fixture
def empty_sales_df():
    return pd.DataFrame(columns=["Date", "Customer ID", "Revenue", "cost", "acquisition_channel"])


@pytest.fixture
def sales_df_with_missing():
    return pd.DataFrame({
        "Date": pd.to_datetime(["2024-01-15", None, "2024-02-10"]),
        "Customer ID": ["C1", "C2", None],
        "Revenue": [100.0, None, 150.0],
        "cost": [50.0, None, 75.0],
        "acquisition_channel": ["Organic", "Paid", None],
        "cohort": ["C1", "C1", ""],
    })


class TestCalculateOverallMetrics:
    def test_basic_calculation(self, sales_df, promotion_df, marketing_df, clients_df):
        result = calculate_overall_metrics(sales_df, promotion_df, marketing_df, clients_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 20

        idx = result[result["Показатель"] == "Количество уникальных клиентов"].index[0]
        assert result.loc[idx, "Значение"] == "3"

        idx = result[result["Показатель"] == "Количество заказов"].index[0]
        assert result.loc[idx, "Значение"] == "4"

    def test_empty_dataframe(self, empty_sales_df, promotion_df, marketing_df):
        result = calculate_overall_metrics(empty_sales_df, promotion_df, marketing_df)
        assert isinstance(result, pd.DataFrame)
        assert "Выручка" in result["Показатель"].values

    def test_with_missing_values(self, sales_df_with_missing, promotion_df, marketing_df):
        result = calculate_overall_metrics(sales_df_with_missing, promotion_df, marketing_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 20

    def test_no_clients_df(self, sales_df, promotion_df, marketing_df):
        result = calculate_overall_metrics(sales_df, promotion_df, marketing_df, clients_df=None)
        assert isinstance(result, pd.DataFrame)


class TestCalculateRevenueTable:
    def test_basic_calculation(self, sales_df, cohorts_df):
        result = calculate_revenue_table(sales_df, cohorts_df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "ВСЕГО" in result.columns

    def test_empty_sales(self, empty_sales_df, cohorts_df):
        result = calculate_revenue_table(empty_sales_df, cohorts_df)
        assert result.empty

    def test_empty_cohorts(self, sales_df):
        empty_cohorts = pd.DataFrame(columns=["cohort", "date_start", "date_end"])
        result = calculate_revenue_table(sales_df, empty_cohorts)
        assert result.empty

    def test_with_missing_cohort(self, sales_df, cohorts_df):
        sales_df_copy = sales_df.copy()
        sales_df_copy.loc[2, "cohort"] = ""
        result = calculate_revenue_table(sales_df_copy, cohorts_df)
        assert isinstance(result, pd.DataFrame)


class TestCalculateCostTable:
    def test_basic_calculation(self, sales_df, cohorts_df):
        result = calculate_cost_table(sales_df, cohorts_df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "ВСЕГО" in result.columns

    def test_empty_dataframe(self, empty_sales_df, cohorts_df):
        result = calculate_cost_table(empty_sales_df, cohorts_df)
        assert result.empty


class TestCalculateProfitTable:
    def test_basic_calculation(self, sales_df, cohorts_df, promotion_df, marketing_df):
        revenue_df = calculate_revenue_table(sales_df, cohorts_df)
        cost_df = calculate_cost_table(sales_df, cohorts_df)

        result = calculate_profit_table(revenue_df, cost_df, promotion_df, marketing_df)
        assert isinstance(result, pd.DataFrame)
        assert "ИТОГО" in result.index

    def test_empty_revenue(self):
        empty_df = pd.DataFrame()
        result = calculate_profit_table(empty_df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        assert result.empty


class TestCalculateOrdersTable:
    def test_basic_calculation(self, sales_df, cohorts_df):
        result = calculate_orders_table(sales_df, cohorts_df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "ВСЕГО" in result.columns

    def test_empty_dataframe(self, empty_sales_df, cohorts_df):
        result = calculate_orders_table(empty_sales_df, cohorts_df)
        assert result.empty


class TestCalculateAvgProfitPerOrderTable:
    def test_basic_calculation(self, sales_df, cohorts_df):
        revenue_df = calculate_revenue_table(sales_df, cohorts_df)
        cost_df = calculate_cost_table(sales_df, cohorts_df)
        promotion_df = pd.DataFrame()
        marketing_df = pd.DataFrame()
        orders_df = calculate_orders_table(sales_df, cohorts_df)

        profit_df = calculate_profit_table(revenue_df, cost_df, promotion_df, marketing_df)
        result = calculate_avg_profit_per_order_table(profit_df, orders_df)
        assert isinstance(result, pd.DataFrame)

    def test_empty_dataframes(self):
        result = calculate_avg_profit_per_order_table(pd.DataFrame(), pd.DataFrame())
        assert result.empty


class TestCalculateProfitByChannelTable:
    def test_basic_calculation(self, sales_df, cohorts_df, promotion_df, marketing_df):
        revenue_df = calculate_revenue_table(sales_df, cohorts_df)
        cost_df = calculate_cost_table(sales_df, cohorts_df)
        profit_df = calculate_profit_table(revenue_df, cost_df, promotion_df, marketing_df)

        result = calculate_profit_by_channel_table(profit_df)
        assert isinstance(result, pd.DataFrame)
        assert "Канал" in result.columns
        assert "Доля" in result.columns

    def test_empty_dataframe(self):
        result = calculate_profit_by_channel_table(pd.DataFrame())
        assert result.empty

    def test_no_total_column(self):
        df = pd.DataFrame({"A": [1], "B": [2]})
        result = calculate_profit_by_channel_table(df)
        assert result.empty


class TestCalculateOrdersByChannelTable:
    def test_basic_calculation(self, sales_df, cohorts_df):
        orders_df = calculate_orders_table(sales_df, cohorts_df)
        result = calculate_orders_by_channel_table(orders_df)
        assert isinstance(result, pd.DataFrame)
        assert "Канал" in result.columns
        assert "Доля" in result.columns

    def test_empty_dataframe(self):
        result = calculate_orders_by_channel_table(pd.DataFrame())
        assert result.empty


class TestCalculateAvgProfitByChannelTable:
    def test_basic_calculation(self, sales_df, cohorts_df, promotion_df, marketing_df):
        revenue_df = calculate_revenue_table(sales_df, cohorts_df)
        cost_df = calculate_cost_table(sales_df, cohorts_df)
        profit_df = calculate_profit_table(revenue_df, cost_df, promotion_df, marketing_df)
        orders_df = calculate_orders_table(sales_df, cohorts_df)

        profit_by_channel = calculate_profit_by_channel_table(profit_df)
        orders_by_channel = calculate_orders_by_channel_table(orders_df)

        result = calculate_avg_profit_by_channel_table(profit_by_channel, orders_by_channel)
        assert isinstance(result, pd.DataFrame)
        assert "Канал" in result.columns

    def test_empty_dataframes(self):
        result = calculate_avg_profit_by_channel_table(pd.DataFrame(), pd.DataFrame())
        assert result.empty


class TestCalculateAvgAcquisitionCostTable:
    def test_basic_calculation(self, sales_df, cohorts_df, promotion_df):
        orders_df = calculate_orders_table(sales_df, cohorts_df)
        result = calculate_avg_acquisition_cost_table(promotion_df, orders_df)
        assert isinstance(result, pd.DataFrame)

    def test_empty_orders(self):
        result = calculate_avg_acquisition_cost_table(pd.DataFrame(), pd.DataFrame())
        assert result.empty


class TestCalculatePromotionCostsTable:
    def test_basic_calculation(self, promotion_df, cohorts_df):
        result = calculate_promotion_costs_table(promotion_df, cohorts_df)
        assert isinstance(result, pd.DataFrame)
        assert "ВСЕГО" in result.columns

    def test_empty_dataframe(self):
        result = calculate_promotion_costs_table(pd.DataFrame(), pd.DataFrame())
        assert result.empty

    def test_missing_cohort_column(self):
        df = pd.DataFrame({"costs": [100], "channels": ["Organic"]})
        result = calculate_promotion_costs_table(df, pd.DataFrame())
        assert result.empty


class TestCalculateOtherMarketingCostsTable:
    def test_basic_calculation(self, marketing_df, cohorts_df):
        result = calculate_other_marketing_costs_table(marketing_df, cohorts_df)
        assert isinstance(result, pd.DataFrame)
        assert "ВСЕГО" in result.columns

    def test_empty_dataframe(self):
        result = calculate_other_marketing_costs_table(pd.DataFrame(), pd.DataFrame())
        assert result.empty

    def test_missing_cohort_column(self):
        df = pd.DataFrame({"costs": [50], "channels": ["Organic"]})
        result = calculate_other_marketing_costs_table(df, pd.DataFrame())
        assert result.empty


# ── propagate_monetary_values ─────────────────────────────────────────

class TestPropagateMonetaryValues:
    def test_no_prev_vals_returns_same(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("100"), Decimal("200"), Decimal("300")]
        result = propagate_monetary_values(vals, None, Decimal("1000"))
        assert result == vals

    def test_no_change_returns_same(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("100"), Decimal("200"), Decimal("300")]
        result = propagate_monetary_values(vals, list(vals), Decimal("1000"))
        assert result == vals

    def test_push_up_m2(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("300"), Decimal("200"), Decimal("300")]
        prev = [Decimal("100"), Decimal("200"), Decimal("300")]
        result = propagate_monetary_values(vals, prev, Decimal("1000"))
        assert result[0] == Decimal("300")
        assert result[1] >= result[0] + Decimal("0.01")
        assert result[2] >= result[1] + Decimal("0.01")

    def test_push_up_m3(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("100"), Decimal("500"), Decimal("300")]
        prev = [Decimal("100"), Decimal("200"), Decimal("300")]
        result = propagate_monetary_values(vals, prev, Decimal("1000"))
        assert result[1] == Decimal("500")
        assert result[2] >= result[1] + Decimal("0.01")

    def test_pull_down_m2(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("50"), Decimal("200"), Decimal("300")]
        prev = [Decimal("100"), Decimal("200"), Decimal("300")]
        result = propagate_monetary_values(vals, prev, Decimal("1000"))
        assert result[0] == Decimal("50")
        # M1 doesn't exist, so nothing to pull
        assert result[1] == Decimal("200")

    def test_pull_down_m3(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("100"), Decimal("80"), Decimal("300")]
        prev = [Decimal("100"), Decimal("200"), Decimal("300")]
        result = propagate_monetary_values(vals, prev, Decimal("1000"))
        assert result[1] == Decimal("80")
        assert result[0] <= result[1] - Decimal("0.01")

    def test_clamp_to_max_monetary(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("100"), Decimal("200"), Decimal("300")]
        prev = [Decimal("100"), Decimal("200"), Decimal("200")]
        result = propagate_monetary_values(vals, prev, Decimal("250"))
        assert result[2] == Decimal("250")
        assert result[1] <= result[2] - Decimal("0.01")

    def test_min_diff_maintained_strictly(self):
        from analysis import propagate_monetary_values
        from decimal import Decimal
        vals = [Decimal("100"), Decimal("200"), Decimal("300")]
        prev = [Decimal("1"), Decimal("200"), Decimal("300")]
        result = propagate_monetary_values(vals, prev, Decimal("1000"))
        assert result[1] - result[0] >= Decimal("0.01")
        assert result[2] - result[1] >= Decimal("0.01")


# ── Additional edge cases ──────────────────────────────────────────────

class TestEdgeCases:
    def test_overall_metrics_sales_only_no_clients(self):
        from analysis import calculate_overall_metrics
        sales = pd.DataFrame({
            "Revenue": [100, 200],
            "Cost": [40, 60],
        })
        result = calculate_overall_metrics(sales, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        assert not result.empty

    def test_revenue_table_no_revenue_column(self):
        from analysis import calculate_revenue_table
        sales = pd.DataFrame({"Date": pd.to_datetime(["2024-01-01"])})
        cohorts = pd.DataFrame({
            "cohort": ["Cohort 1"],
            "date_start": pd.to_datetime(["2024-01-01"]),
            "date_end": pd.to_datetime(["2024-03-31"]),
        })
        result = calculate_revenue_table(sales, cohorts)
        assert result.empty

    def test_profit_table_empty_all(self):
        from analysis import calculate_profit_table
        result = calculate_profit_table(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        assert result.empty

    def test_orders_table_with_missing_data(self):
        from analysis import calculate_orders_table
        sales = pd.DataFrame({"Date": pd.to_datetime(["2024-01-01"])})
        cohorts = pd.DataFrame()
        result = calculate_orders_table(sales, cohorts)
        assert result.empty

    def test_avg_acquisition_with_zero_orders(self):
        from analysis import calculate_avg_acquisition_cost_table
        promo = pd.DataFrame({
            "cohort": ["Cohort 1"],
            "date_start": pd.to_datetime(["2024-01-01"]),
            "date_end": pd.to_datetime(["2024-03-31"]),
        })
        orders = pd.DataFrame({"Cohort 1": [0]}, index=["Cohort 1"])
        result = calculate_avg_acquisition_cost_table(promo, orders)
        assert not result.empty
        assert result.iloc[0, 0] == 0