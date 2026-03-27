"""
Stamper — adds temporal columns to price DataFrames.

Derived from cycle_stamper.py (cycles-dashboard), with presidential
and decennial cycle logic removed. Keeps only what Bernstein analysis needs:
year, month, week, day_of_year, day_of_week, quarter, trading_day columns.
"""

import pandas as pd
import numpy as np
from typing import Optional


MONTH_NAMES = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

DAY_NAMES = {
    0: 'Monday', 1: 'Tuesday', 2: 'Wednesday',
    3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'
}


def stamp_data(df: pd.DataFrame, date_column: Optional[str] = None) -> pd.DataFrame:
    """
    Add temporal columns to a price DataFrame.

    Args:
        df:           DataFrame with price data. Must have either a DatetimeIndex,
                      a 'timestamp' column (Unix seconds), or a date column.
        date_column:  Name of date column if not using DatetimeIndex.

    Returns:
        DataFrame with added columns:
            year, month, day, day_of_year, week (ISO 1-52/53),
            day_of_week (0=Mon), quarter, month_name, day_name,
            is_month_start, is_month_end,
            trading_day_of_month, trading_day_of_year,
            adjusted_year (handles ISO week boundary split)
    """
    if df.empty:
        return df

    df = df.copy()

    # ── Build DatetimeIndex ──────────────────────────────────────────────────
    if date_column:
        df.index = pd.to_datetime(df[date_column])
    elif 'timestamp' in df.columns:
        df.index = pd.to_datetime(df['timestamp'], unit='s')
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # ── Calendar columns ─────────────────────────────────────────────────────
    df['year']        = df.index.year
    df['month']       = df.index.month
    df['day']         = df.index.day
    df['day_of_year'] = df.index.dayofyear
    df['week']        = df.index.isocalendar().week.values.astype(int)
    df['day_of_week'] = df.index.dayofweek        # 0=Monday
    df['quarter']     = df.index.quarter

    df['month_name'] = df['month'].map(MONTH_NAMES)
    df['day_name']   = df['day_of_week'].map(DAY_NAMES)

    df['is_month_start'] = df.index.is_month_start
    df['is_month_end']   = df.index.is_month_end

    # ── Trading-day counters ──────────────────────────────────────────────────
    df['trading_day_of_month'] = (
        df.groupby([df['year'], df['month']]).cumcount() + 1
    )
    df['trading_day_of_year'] = (
        df.groupby(df['year']).cumcount() + 1
    )

    # ── ISO week boundary fix (adjusted_year) ────────────────────────────────
    # Week 1 rows in December belong to the next calendar year
    # Week 52/53 rows in January belong to the previous calendar year
    df['adjusted_year'] = df['year'].copy()
    mask_w1_dec  = (df['week'] == 1)  & (df['month'] == 12)
    mask_w52_jan = (df['week'] >= 52) & (df['month'] == 1)
    df.loc[mask_w1_dec,  'adjusted_year'] = df.loc[mask_w1_dec,  'year'] + 1
    df.loc[mask_w52_jan, 'adjusted_year'] = df.loc[mask_w52_jan, 'year'] - 1

    return df
