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


def render_cohort_settings(start_date: datetime, end_date: datetime, current_mode: str = "Cohort Size"):
    """Render cohort settings in sidebar and return values."""
    import streamlit as st

    num_cohorts_new, cohort_dates = recalculate_from_cohort_size(
        start_date=start_date,
        end_date=end_date,
        cohort_type=COHORT_TYPE_MONTHS,
        cohort_size=st.session_state.cohort_size_input
    )
    st.session_state.num_cohorts_input = num_cohorts_new
    
    st.sidebar.header("Cohort Settings")
    cohort_type = st.sidebar.selectbox(
        "Type of Cohort Size",
        [COHORT_TYPE_MONTHS, COHORT_TYPE_DAYS],
        index=0
    )

    calculation_mode = st.sidebar.radio(
        "База расчета",
        ["Количество дней/месяцев в когорте", "Количество когорт"],
        index=0 if current_mode == "Cohort Size" else 1
    )
    st.session_state.calculation_mode = "Cohort Size" if calculation_mode == "Количество дней/месяцев в когорте" else "Number of Cohorts"

    max_cohort_size = 365 if cohort_type == COHORT_TYPE_DAYS else 24

    if st.session_state.calculation_mode == "Cohort Size":
        label_size = f"Количество {'дней' if cohort_type == COHORT_TYPE_DAYS else 'месяцев'} в когорте"
        cohort_size_input = st.sidebar.number_input(
            label_size,
            min_value=1,
            max_value=max_cohort_size,
            value=st.session_state.cohort_size_input,
            key="cohort_size_widget"
        )

        if cohort_size_input != st.session_state.cohort_size_input:
            st.session_state.cohort_size_input = cohort_size_input
            num_cohorts_new, cohort_dates = recalculate_from_cohort_size(
                start_date=start_date,
                end_date=end_date,
                cohort_type=cohort_type,
                cohort_size=cohort_size_input
            )
            st.session_state.num_cohorts_input = num_cohorts_new

        st.sidebar.info(f"📊 Рассчитанное количество когорт: **{num_cohorts_new}**")
    else:
        num_cohorts_input = st.sidebar.number_input(
            "Количество когорт",
            min_value=1,
            max_value=MAX_COHORTS,
            value=st.session_state.num_cohorts_input,
            key="num_cohorts_widget"
        )

        if num_cohorts_input != st.session_state.num_cohorts_input:
            cohort_size_new, cohort_dates = recalculate_from_num_cohorts(
                start_date=start_date,
                end_date=end_date,
                cohort_type=cohort_type,
                num_cohorts=num_cohorts_input
            )
            st.session_state.num_cohorts_input = num_cohorts_input
            st.session_state.cohort_size_input = cohort_size_new
            st.session_state._needs_rerun = True
        else:
            cohort_size_new, cohort_dates = recalculate_from_num_cohorts(
                start_date=start_date,
                end_date=end_date,
                cohort_type=cohort_type,
                num_cohorts=num_cohorts_input
            )
            st.session_state.cohort_size_input = cohort_size_new

        cohort_size = cohort_size_new
        num_cohorts = num_cohorts_input
        st.sidebar.info(f"📊 Количество {'дней' if cohort_type == COHORT_TYPE_DAYS else 'месяцев'} в когорте: **{cohort_size_new}**")

    cohort_dates = st.session_state.cohort_dates_input
    if not cohort_dates:
        _, cohort_dates = recalculate_from_cohort_size(
            start_date=start_date,
            end_date=end_date,
            cohort_type=cohort_type,
            cohort_size=st.session_state.cohort_size_input
        )

    st.session_state.prev_cohort_size = st.session_state.cohort_size_input
    st.session_state.prev_num_cohorts = st.session_state.num_cohorts_input

    cohort_dates = st.session_state.get("cohort_dates_input", [])
    if not cohort_dates:
        _, cohort_dates = recalculate_from_cohort_size(
            start_date=start_date,
            end_date=end_date,
            cohort_type=cohort_type,
            cohort_size=st.session_state.cohort_size_input
        )

    for i in range(len(cohort_dates)):
        default_val = cohort_dates[i].strftime('%Y-%m-%d')
        st.sidebar.text_input(
            f"Когорта {i + 1}",
            value=default_val,
            key=f"cohort_date_{i}_{id(cohort_dates)}",
            disabled=True
        )

    is_days = cohort_type != "Cohort Size" or st.session_state.get("_cohort_type_days", False)

    if st.session_state.calculation_mode == "Cohort Size":
        return_num_cohorts = num_cohorts_new
    else:
        return_num_cohorts = num_cohorts_input

    return cohort_type, return_num_cohorts, st.session_state.cohort_size_input, cohort_dates, is_days