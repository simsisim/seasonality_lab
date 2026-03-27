"""
bernstein_chart.py — Bernstein Weekly Composite Seasonal Chart (Plotly)

Reproduces the chart style from charts_template_jack_bernstein.png:
  - Normalized 0-100 weekly price line (green segment = up, red = down)
  - Monthly vertical separator lines + month-name x-axis
  - Bottom panel: ↑ arrows at weeks with win_rate >= threshold
  - Bottom panel: win-rate % per week (green ≥50%, red <50%)

Pipeline:
  daily OHLCV
    → resample to weekly (Friday close)
    → per-year normalize 0-100 using year min/max
    → pivot: rows=year, cols=ISO week 1-52
    → column-wise mean → composite[52]
    → column-wise win_rate → win_rates[52]
    → draw with Plotly

Entry point:
    fig, composite_df = generate_bernstein_chart(df, config)
"""

from __future__ import annotations

import warnings
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.figure as mpl_figure
import matplotlib.gridspec as gridspec

from .bernstein_config import BernsteinJobConfig, FIGURE_FIGSIZE, FIGURE_DPI


# ── Constants ─────────────────────────────────────────────────────────────────

GREEN = '#2ca02c'
RED   = '#d62728'
GRAY  = '#888888'

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_FULL = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

MIN_WEEKS_PER_YEAR = 40


# ── Step 1: resample to weekly ────────────────────────────────────────────────

def _resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample stamped daily DataFrame to weekly (Friday close)."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex. Run stamper.stamp_data() first.")
    weekly = df["close"].resample("W-FRI").last().dropna()
    return weekly.to_frame(name="close")


# ── Step 2: per-year normalization ────────────────────────────────────────────

def normalize_bernstein(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize closing prices to 0-100 scale per year, return pivot table.

    Returns:
        pivot_df: shape (n_years, 52), index=adjusted_year, columns=1..52
    """
    rows_per_month = len(df) / max(1, df.index.to_period("M").nunique())
    if rows_per_month > 8:
        weekly = _resample_to_weekly(df)
        weekly["adjusted_year"] = _adjusted_year(weekly.index)
        weekly["week"] = weekly.index.isocalendar().week.values.astype(int)
    else:
        weekly = df[["close", "adjusted_year", "week"]].copy()

    weekly = weekly[weekly["week"] <= 52]

    pivot_raw = weekly.pivot_table(
        index="adjusted_year", columns="week", values="close", aggfunc="last"
    )
    pivot_raw = pivot_raw[pivot_raw.notna().sum(axis=1) >= MIN_WEEKS_PER_YEAR]

    if pivot_raw.empty:
        raise ValueError("Not enough data (need ≥1 year with 40+ weeks).")

    year_min   = pivot_raw.min(axis=1)
    year_max   = pivot_raw.max(axis=1)
    year_range = year_max - year_min

    valid_years = year_range[year_range > 0].index
    pivot_raw   = pivot_raw.loc[valid_years]
    year_min    = year_min[valid_years]
    year_range  = year_range[valid_years]

    pivot_norm = pivot_raw.subtract(year_min, axis=0).divide(year_range, axis=0) * 100.0
    pivot_norm.columns = pivot_norm.columns.astype(int)
    return pivot_norm


def _adjusted_year(dt_index: pd.DatetimeIndex) -> pd.Series:
    iso   = dt_index.isocalendar()
    year  = pd.Series(dt_index.year,  index=dt_index)
    month = pd.Series(dt_index.month, index=dt_index)
    week  = pd.Series(iso.week.values.astype(int), index=dt_index)
    adj   = year.copy()
    adj[(week == 1)  & (month == 12)] += 1
    adj[(week >= 52) & (month == 1)]  -= 1
    return adj


# ── Step 3: composite and win-rates ──────────────────────────────────────────

def build_composite(pivot_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """
    Returns:
        composite:  shape (52,) — mean normalized close per ISO week
        win_rates:  shape (52,) — fraction of years where week > prior week
        years_used: list of int
    """
    pivot = pivot_df.reindex(columns=range(1, 53))
    composite  = pivot.mean(axis=0, skipna=True).values
    years_used = sorted(pivot.index.tolist())

    win_rates = np.full(52, np.nan)
    for w_idx in range(1, 52):
        curr = pivot[w_idx + 1]
        prev = pivot[w_idx]
        both = curr.notna() & prev.notna()
        if both.sum() > 0:
            win_rates[w_idx] = (curr[both] > prev[both]).sum() / both.sum()

    # Week 1: compare to week 52 of prior year
    years_sorted = sorted(pivot.index)
    up_count = valid_count = 0
    for i, yr in enumerate(years_sorted):
        if i == 0:
            continue
        prev_yr  = years_sorted[i - 1]
        w1_now   = pivot.at[yr,      1]  if yr      in pivot.index else np.nan
        w52_prev = pivot.at[prev_yr, 52] if prev_yr in pivot.index else np.nan
        if pd.notna(w1_now) and pd.notna(w52_prev):
            valid_count += 1
            if w1_now > w52_prev:
                up_count += 1
    if valid_count > 0:
        win_rates[0] = up_count / valid_count

    return composite, win_rates, years_used


# ── Step 4: map ISO weeks → calendar months ───────────────────────────────────

def _map_weeks_to_months(df: pd.DataFrame) -> tuple[dict, list, list]:
    """
    Returns:
        week_to_month:  {iso_week: month_number}
        boundary_weeks: list of x positions where month changes
        month_centers:  [(center_week_float, month_idx 0-based), ...]
    """
    rows_per_month = len(df) / max(1, df.index.to_period("M").nunique())
    if rows_per_month > 8:
        idx = pd.date_range("2000-01-01", "2020-12-31", freq="W-FRI")
    else:
        idx = df.index

    weeks  = idx.isocalendar().week.values.astype(int)
    months = idx.month

    week_to_month: dict[int, int] = {}
    for w in range(1, 53):
        mask = weeks == w
        if mask.sum() > 0:
            week_to_month[w] = int(pd.Series(months[mask]).value_counts().idxmax())

    for w in range(1, 53):
        if w not in week_to_month:
            for delta in range(1, 5):
                if (w - delta) in week_to_month:
                    week_to_month[w] = week_to_month[w - delta]
                    break

    boundary_weeks = []
    prev_month = week_to_month.get(1, 1)
    for w in range(2, 53):
        m = week_to_month.get(w, prev_month)
        if m != prev_month:
            boundary_weeks.append(w - 0.5)
            prev_month = m

    month_groups: dict[int, list] = {}
    for w, m in week_to_month.items():
        month_groups.setdefault(m, []).append(w)

    month_centers = []
    for m in range(1, 13):
        ws = month_groups.get(m, [])
        if ws:
            month_centers.append((float(np.mean(ws)), m - 1))

    return week_to_month, boundary_weeks, month_centers


# ── Step 5: draw the chart (matplotlib) ──────────────────────────────────────

def draw_bernstein_composite(
    composite:      np.ndarray,
    win_rates:      np.ndarray,
    years_used:     list[int],
    ticker:         str,
    start_year:     Optional[int],
    end_year:       Optional[int],
    week_to_month:  dict,
    boundary_weeks: list,
    month_centers:  list,
    threshold:      float = 65.0,
) -> mpl_figure.Figure:
    """
    Render the Bernstein composite chart using matplotlib.

    Layout (two rows via GridSpec):
      Row 1 (82%): 0-100 composite line, month separators, month labels
      Row 2 (18%): ↑ arrows + win-rate % numbers (axes hidden)
    """
    n     = 52
    weeks = np.arange(1, n + 1, dtype=float)
    valid = ~np.isnan(composite)

    threshold_frac = threshold / 100.0

    # ── Create figure with two subplots ──────────────────────────────────────
    fig = plt.figure(figsize=FIGURE_FIGSIZE)
    fig.patch.set_facecolor('white')

    gs  = gridspec.GridSpec(2, 1, height_ratios=[0.82, 0.18], hspace=0)
    ax1 = fig.add_subplot(gs[0])   # main composite line
    ax2 = fig.add_subplot(gs[1])   # win-rate panel

    # ── Style: row 1 ─────────────────────────────────────────────────────────
    ax1.set_facecolor('white')
    for spine in ax1.spines.values():
        spine.set_visible(False)
    ax1.yaxis.grid(True, color='rgba(200,200,200,0.6)' if False else '#dddddd',
                   linewidth=0.5, zorder=0)
    ax1.xaxis.grid(False)
    ax1.set_axisbelow(True)
    ax1.tick_params(axis='both', which='both', length=0, labelsize=8, colors='#666666')

    # ── Style: row 2 ─────────────────────────────────────────────────────────
    ax2.set_facecolor('white')
    for spine in ax2.spines.values():
        spine.set_visible(False)
    ax2.set_yticks([])
    ax2.tick_params(axis='both', which='both', length=0)

    # ── Composite line: colored segments (green=up, red=down) ─────────────
    i = 1
    while i < n:
        if not valid[i] or not valid[i - 1]:
            i += 1
            continue
        going_up = composite[i] >= composite[i - 1]
        color    = GREEN if going_up else RED

        seg_x = [weeks[i - 1], weeks[i]]
        seg_y = [composite[i - 1], composite[i]]

        j = i + 1
        while j < n and valid[j] and valid[j - 1]:
            if (composite[j] >= composite[j - 1]) != going_up:
                break
            seg_x.append(weeks[j])
            seg_y.append(composite[j])
            j += 1

        ax1.plot(seg_x, seg_y, color=color, linewidth=1.8, zorder=3)
        ax1.plot(seg_x, seg_y, 'o', color=color, markersize=3, zorder=4)
        i = j

    # ── Weekly grid lines (thin) + monthly separators (thick) ────────────
    boundary_weeks_set = set(boundary_weeks)
    for w in range(2, 53):
        bw = w - 0.5
        if bw not in boundary_weeks_set:
            ax1.axvline(x=bw, color='#cccccc', linewidth=0.4, zorder=1)
            ax2.axvline(x=bw, color='#cccccc', linewidth=0.4, zorder=1)
    for bw in boundary_weeks:
        ax1.axvline(x=bw, color='#888888', linewidth=1.2, zorder=2)
        ax2.axvline(x=bw, color='#888888', linewidth=1.2, zorder=2)

    # ── Bottom panel: ↑ arrows at high-WR weeks ───────────────────────────
    for k in range(n):
        if not np.isnan(win_rates[k]) and win_rates[k] >= threshold_frac:
            ax2.text(weeks[k], 0.72, '↑',
                     ha='center', va='center', fontsize=9,
                     color=GREEN, fontfamily='monospace', zorder=3)

    # ── Bottom panel: win-rate % numbers ──────────────────────────────────
    ax2.text(0.3, 0.28, 'WR%',
             ha='right', va='center', fontsize=6,
             color=GRAY, fontfamily='monospace', zorder=3)
    for k in range(n):
        wr = win_rates[k]
        if np.isnan(wr):
            continue
        pct   = int(round(wr * 100))
        color = GREEN if wr >= 0.50 else RED
        ax2.text(weeks[k], 0.28, str(pct),
                 ha='center', va='center', fontsize=7,
                 color=color, fontfamily='monospace', zorder=3)

    # ── X-axis: month names on bottom panel (ax2), none on ax1 ───────────
    tick_vals = [mc[0] for mc in month_centers]
    tick_text = [MONTH_FULL[mc[1]] for mc in month_centers]
    ax1.set_xticks([])
    ax1.set_xlim(0.5, 52.5)
    ax2.set_xticks(tick_vals)
    ax2.set_xticklabels(tick_text, fontsize=9, color='#444444')
    ax2.tick_params(axis='x', which='both', length=0)
    ax2.set_xlim(0.5, 52.5)

    # ── Y-axis: row 1 ─────────────────────────────────────────────────────
    ax1.set_ylim(-3, 105)
    ax1.set_yticks(range(0, 101, 10))
    ax1.set_ylabel('Normalized (0–100)', fontsize=9, color=GRAY, labelpad=4)

    # ── Y-axis: row 2 (hidden) ────────────────────────────────────────────
    ax2.set_ylim(0, 1)

    # ── Title ─────────────────────────────────────────────────────────────
    yr_range = f"{start_year or min(years_used)} - {end_year or max(years_used)}"
    n_years  = len(years_used)
    title    = (f"WEEKLY SEASONAL STOCK COMPOSITE   "
                f"{ticker.upper()}   {yr_range}   ({n_years} years)")
    fig.text(0.5, 0.98, title, ha='center', va='top',
             fontsize=11, color='#222222', fontfamily='monospace',
             transform=fig.transFigure)

    fig.subplots_adjust(top=0.93, bottom=0.04, left=0.07, right=0.99)

    return fig


# ── Step 6: main entry point ──────────────────────────────────────────────────

def generate_bernstein_chart(
    df: pd.DataFrame,
    config: BernsteinJobConfig,
) -> tuple[mpl_figure.Figure, pd.DataFrame]:
    """
    Full pipeline: stamped daily/weekly DataFrame → Bernstein composite Figure.

    Returns:
        fig:          matplotlib Figure ready to save as PNG.
        composite_df: DataFrame with columns [iso_week, composite_value,
                       win_rate_pct, month] for CSV export.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pivot_df = normalize_bernstein(df)

    composite, win_rates, years_used = build_composite(pivot_df)

    # Use a fixed reference calendar for stable month mapping
    ref_idx = pd.date_range("2000-01-01", "2020-12-31", freq="W-FRI")
    ref_weeks  = ref_idx.isocalendar().week.values.astype(int)
    ref_months = ref_idx.month

    week_to_month: dict[int, int] = {}
    for w in range(1, 53):
        mask = ref_weeks == w
        if mask.sum() > 0:
            week_to_month[w] = int(pd.Series(ref_months[mask]).value_counts().idxmax())

    _, boundary_weeks, month_centers = _map_weeks_to_months(df)

    fig = draw_bernstein_composite(
        composite      = composite,
        win_rates      = win_rates,
        years_used     = years_used,
        ticker         = config.ticker,
        start_year     = config.start_year,
        end_year       = config.end_year,
        week_to_month  = week_to_month,
        boundary_weeks = boundary_weeks,
        month_centers  = month_centers,
        threshold      = config.win_rate_arrow_threshold,
    )

    composite_df = pd.DataFrame({
        "iso_week":        np.arange(1, 53),
        "composite_value": np.round(composite, 2),
        "win_rate_pct":    np.round(win_rates * 100, 1),
        "month":           [week_to_month.get(w, 0) for w in range(1, 53)],
    })

    return fig, composite_df
