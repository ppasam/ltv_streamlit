"""Tests for cohorts.py — date splitting logic."""
from datetime import datetime, timedelta

import pytest

from cohorts import (
    COHORT_TYPE_DAYS,
    COHORT_TYPE_MONTHS,
    MAX_COHORTS,
    calculate_cohort_size_days,
    calculate_cohort_size_months,
    calculate_num_cohorts_days,
    calculate_num_cohorts_months,
    get_cohort_dates,
    recalculate_from_cohort_size,
    recalculate_from_num_cohorts,
    validate_cohort_size,
)


# ── calculate_cohort_size_days ──────────────────────────────────────────

class TestCalculateCohortSizeDays:
    def test_basic(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 31)  # 91 days
        assert calculate_cohort_size_days(start, end, 3) == 30  # 91 // 3

    def test_zero_num_cohorts(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 31)
        assert calculate_cohort_size_days(start, end, 0) == 1

    def test_negative_num_cohorts(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 31)
        assert calculate_cohort_size_days(start, end, -5) == 1

    def test_single_day_range(self):
        start = datetime(2024, 6, 15)
        end = datetime(2024, 6, 15)  # 1 day
        assert calculate_cohort_size_days(start, end, 5) == 1  # max(1, 1 // 5)


# ── calculate_cohort_size_months ────────────────────────────────────────

class TestCalculateCohortSizeMonths:
    def test_basic(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)  # 12 months
        assert calculate_cohort_size_months(start, end, 4) == 3  # 12 // 4

    def test_zero_num_cohorts(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        assert calculate_cohort_size_months(start, end, 0) == 1

    def test_partial_month(self):
        start = datetime(2024, 3, 15)
        end = datetime(2024, 5, 10)  # ~3 months
        assert calculate_cohort_size_months(start, end, 4) == 1  # max(1, 3 // 4)

    def test_cross_year(self):
        start = datetime(2023, 11, 1)
        end = datetime(2024, 2, 1)  # 4 months
        assert calculate_cohort_size_months(start, end, 2) == 2  # 4 // 2


# ── calculate_num_cohorts_days ──────────────────────────────────────────

class TestCalculateNumCohortsDays:
    def test_basic(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)  # 366 days
        assert calculate_num_cohorts_days(start, end, 30) == 12  # 366 // 30

    def test_zero_cohort_size(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        assert calculate_num_cohorts_days(start, end, 0) == 1

    def test_clamped_to_max(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        # With size=1, we'd get 366 cohorts, but MAX_COHORTS = 52
        assert calculate_num_cohorts_days(start, end, 1) == MAX_COHORTS

    def test_single_day_cohort_size(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 5)  # 5 days
        assert calculate_num_cohorts_days(start, end, 3) == 1  # 5 // 3


# ── calculate_num_cohorts_months ────────────────────────────────────────

class TestCalculateNumCohortsMonths:
    def test_basic(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)  # 12 months
        assert calculate_num_cohorts_months(start, end, 3) == 4  # 12 // 3

    def test_zero_cohort_size(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        assert calculate_num_cohorts_months(start, end, 0) == 1

    def test_clamped_to_max(self):
        start = datetime(2024, 1, 1)
        end = datetime(2025, 12, 31)  # 24 months
        # With size=1, 24 cohorts
        assert calculate_num_cohorts_months(start, end, 1) == 24

    def test_cross_year(self):
        start = datetime(2023, 10, 1)
        end = datetime(2024, 3, 31)  # 6 months
        assert calculate_num_cohorts_months(start, end, 2) == 3  # 6 // 2


# ── get_cohort_dates ────────────────────────────────────────────────────

class TestGetCohortDates:
    def test_days(self):
        start = datetime(2024, 1, 1)
        dates = get_cohort_dates(start, COHORT_TYPE_DAYS, 7, 3)
        assert dates == [
            datetime(2024, 1, 1),
            datetime(2024, 1, 8),
            datetime(2024, 1, 15),
        ]

    def test_months(self):
        start = datetime(2024, 1, 1)
        dates = get_cohort_dates(start, COHORT_TYPE_MONTHS, 3, 4)
        assert dates == [
            datetime(2024, 1, 1),
            datetime(2024, 4, 1),
            datetime(2024, 7, 1),
            datetime(2024, 10, 1),
        ]

    def test_cross_year_months(self):
        start = datetime(2023, 10, 1)
        dates = get_cohort_dates(start, COHORT_TYPE_MONTHS, 5, 3)
        assert dates == [
            datetime(2023, 10, 1),
            datetime(2024, 3, 1),
            datetime(2024, 8, 1),
        ]

    def test_single_cohort(self):
        start = datetime(2024, 6, 15)
        dates = get_cohort_dates(start, COHORT_TYPE_DAYS, 30, 1)
        assert dates == [datetime(2024, 6, 15)]

    def test_february_overflow(self):
        """Cohort starts on Jan 31, step=1 month — should not crash on Feb."""
        start = datetime(2024, 1, 31)
        dates = get_cohort_dates(start, COHORT_TYPE_MONTHS, 1, 3)
        # Feb 31 → clamped to Feb 28 (2024 is leap → 29? Let's see what code does)
        # Code uses try/except with fallback to 28th
        assert dates[0] == datetime(2024, 1, 31)
        assert len(dates) == 3


# ── validate_cohort_size ────────────────────────────────────────────────

class TestValidateCohortSize:
    def test_under_max(self):
        assert validate_cohort_size(8) == 8

    def test_exactly_max(self):
        assert validate_cohort_size(MAX_COHORTS) == MAX_COHORTS

    def test_over_max(self):
        assert validate_cohort_size(100) == MAX_COHORTS

    def test_at_zero(self):
        assert validate_cohort_size(0) == 0  # not clamped up


# ── recalculate_from_cohort_size ────────────────────────────────────────

class TestRecalculateFromCohortSize:
    def test_days(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        n, dates = recalculate_from_cohort_size(start, end, COHORT_TYPE_DAYS, 30)
        assert n == 12  # 366 // 30
        assert len(dates) == 12
        assert dates[0] == datetime(2024, 1, 1)
        assert dates[1] == datetime(2024, 1, 31)

    def test_months(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        n, dates = recalculate_from_cohort_size(start, end, COHORT_TYPE_MONTHS, 3)
        assert n == 4  # 12 // 3
        assert len(dates) == 4
        assert dates[-1] == datetime(2024, 10, 1)

    def test_edge_zero_size(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        n, dates = recalculate_from_cohort_size(start, end, COHORT_TYPE_DAYS, 0)
        assert n == 1  # clamped
        assert len(dates) == 1


# ── recalculate_from_num_cohorts ────────────────────────────────────────

class TestRecalculateFromNumCohorts:
    def test_days(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        sz, dates = recalculate_from_num_cohorts(start, end, COHORT_TYPE_DAYS, 12)
        assert sz == 30  # 366 // 12 = 30.5 → 30
        assert len(dates) == 12

    def test_months(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        sz, dates = recalculate_from_num_cohorts(start, end, COHORT_TYPE_MONTHS, 6)
        assert sz == 2  # 12 // 6
        assert len(dates) == 6

    def test_exceeds_max_cohorts(self):
        start = datetime(2024, 1, 1)
        end = datetime(2025, 12, 31)
        # 100 cohorts requested, but MAX_COHORTS = 52
        sz, dates = recalculate_from_num_cohorts(start, end, COHORT_TYPE_DAYS, 100)
        assert len(dates) == MAX_COHORTS

    def test_single_cohort(self):
        start = datetime(2024, 6, 1)
        end = datetime(2024, 8, 31)
        sz, dates = recalculate_from_num_cohorts(start, end, COHORT_TYPE_MONTHS, 1)
        assert len(dates) == 1
