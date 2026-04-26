"""Cohort analysis module for LTV application."""
from datetime import datetime, timedelta
from typing import List, Tuple

import pandas as pd


CohortType = str


COHORT_TYPE_DAYS = "Количество дней"
COHORT_TYPE_MONTHS = "Количество месяцев"

MAX_COHORTS = 52


def calculate_cohort_size_days(start_date: datetime, end_date: datetime,
                                num_cohorts: int) -> int:
    """Calculate cohort size in days based on date range and number of cohorts."""
    if num_cohorts <= 0:
        return 1
    total_days = (end_date - start_date).days + 1
    return max(1, total_days // num_cohorts)


def calculate_cohort_size_months(start_date: datetime, end_date: datetime,
                                  num_cohorts: int) -> int:
    """Calculate cohort size in months based on date range and number of cohorts."""
    if num_cohorts <= 0:
        return 1
    total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    return max(1, total_months // num_cohorts)


def calculate_num_cohorts_days(start_date: datetime, end_date: datetime,
                                cohort_size_days: int) -> int:
    """Calculate number of cohorts based on date range and cohort size in days."""
    if cohort_size_days <= 0:
        return 1
    total_days = (end_date - start_date).days + 1
    num_cohorts = total_days // cohort_size_days
    return min(num_cohorts, MAX_COHORTS)


def calculate_num_cohorts_months(start_date: datetime, end_date: datetime,
                                  cohort_size_months: int) -> int:
    """Calculate number of cohorts based on date range and cohort size in months."""
    if cohort_size_months <= 0:
        return 1
    total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    num_cohorts = total_months // cohort_size_months
    return min(num_cohorts, MAX_COHORTS)


def get_cohort_dates(start_date: datetime, cohort_type: CohortType,
                     cohort_size: int, num_cohorts: int) -> List[datetime]:
    """Calculate list of cohort start dates."""
    cohort_dates = []
    current_date = start_date

    for _ in range(num_cohorts):
        cohort_dates.append(current_date)
        if cohort_type == COHORT_TYPE_DAYS:
            current_date = current_date + timedelta(days=cohort_size)
        else:
            month = current_date.month + cohort_size
            year = current_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            try:
                current_date = current_date.replace(year=year, month=month)
            except ValueError:
                current_date = datetime(year, month, 28)

    return cohort_dates


def validate_cohort_size(num_cohorts: int) -> int:
    """Ensure number of cohorts doesn't exceed maximum."""
    return min(num_cohorts, MAX_COHORTS)


def calculate_cohorts(start_date: datetime, end_date: datetime,
                      cohort_type: CohortType, cohort_size: int,
                      num_cohorts: int) -> Tuple[int, int, List[datetime]]:
    """Calculate cohort parameters with validation.

    Returns:
        Tuple of (validated_num_cohorts, cohort_size, list_of_cohort_start_dates)
    """
    total_days = (end_date - start_date).days + 1
    total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

    if cohort_type == COHORT_TYPE_DAYS:
        max_possible_cohorts = total_days // cohort_size if cohort_size > 0 else total_days
    else:
        max_possible_cohorts = total_months // cohort_size if cohort_size > 0 else total_months

    validated_num_cohorts = min(num_cohorts, MAX_COHORTS, max_possible_cohorts)
    if validated_num_cohorts < 1:
        validated_num_cohorts = 1

    if cohort_type == COHORT_TYPE_DAYS:
        calculated_size = calculate_cohort_size_days(start_date, end_date, validated_num_cohorts)
    else:
        calculated_size = calculate_cohort_size_months(start_date, end_date, validated_num_cohorts)

    cohort_dates = get_cohort_dates(start_date, cohort_type, calculated_size, validated_num_cohorts)

    return validated_num_cohorts, calculated_size, cohort_dates


def recalculate_from_num_cohorts(start_date: datetime, end_date: datetime,
                                   cohort_type: CohortType,
                                   num_cohorts: int) -> Tuple[int, List[datetime]]:
    """Recalculate cohort size from number of cohorts.

    Returns:
        Tuple of (cohort_size, list_of_cohort_start_dates)
    """
    validated_num = validate_cohort_size(num_cohorts)

    if cohort_type == COHORT_TYPE_DAYS:
        cohort_size = calculate_cohort_size_days(start_date, end_date, validated_num)
    else:
        cohort_size = calculate_cohort_size_months(start_date, end_date, validated_num)

    cohort_dates = get_cohort_dates(start_date, cohort_type, cohort_size, validated_num)

    return cohort_size, cohort_dates


def recalculate_from_cohort_size(start_date: datetime, end_date: datetime,
                                   cohort_type: CohortType,
                                   cohort_size: int) -> Tuple[int, List[datetime]]:
    """Recalculate number of cohorts from cohort size.

    Returns:
        Tuple of (num_cohorts, list_of_cohort_start_dates)
    """
    if cohort_type == COHORT_TYPE_DAYS:
        num_cohorts = calculate_num_cohorts_days(start_date, end_date, cohort_size)
    else:
        num_cohorts = calculate_num_cohorts_months(start_date, end_date, cohort_size)

    num_cohorts = validate_cohort_size(num_cohorts)

    cohort_dates = get_cohort_dates(start_date, cohort_type, cohort_size, num_cohorts)

    return num_cohorts, cohort_dates


def assign_cohort(df: pd.DataFrame, date_column: str,
                  cohort_type: CohortType, cohort_size: int) -> pd.DataFrame:
    """Assign cohort to each record based on date column."""
    df = df.copy()

    if cohort_type == COHORT_TYPE_DAYS:
        df["cohort_date"] = df[date_column].apply(
            lambda x: x - timedelta(days=x.day - 1)
        )
    else:
        df["cohort_date"] = df[date_column].apply(
            lambda x: x.replace(day=1)
        )

    return df