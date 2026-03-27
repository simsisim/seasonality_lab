"""
best_trade.py — Bernstein Best Trade Scanner (core algorithm).

Methodology
-----------
Scans all (entry_doy, exit_doy) combinations within the user-selected entry
months and days-in-trade range.  Uses RAW daily close prices year-by-year —
completely independent of the Bernstein Composite chart which normalises each
year 0-100.  Each calendar year is one independent observation per window.

For each window the scanner answers:
  "If I had entered on ~MM/DD and exited on ~MM/DD in EVERY year of the
   lookback period, how often did I make money, by how much, and what was
   the worst I could have experienced?"

Public API
----------
  run_best_trade_scan(df, ticker, ...)  → pd.DataFrame   (ranked windows)
  draw_top_trades_chart(df, ticker, top_n) → Figure
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.figure as mpl_figure

from src.core.bernstein_config import FIGURE_FIGSIZE, FIGURE_DPI

# ── Colour palette ────────────────────────────────────────────────────────────
GREEN = '#2ca02c'
AMBER = '#ff7f0e'
RED   = '#d62728'
GRAY  = '#888888'

# Reference (non-leap) year used only for DOY → MM/DD label conversion
_REF_YEAR = 2023


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doy_to_mmdd(doy: int) -> str:
    """Convert day-of-year (1-365) to 'MM/DD' using a non-leap reference year."""
    doy = max(1, min(doy, 365))
    d = date(_REF_YEAR, 1, 1) + pd.Timedelta(days=doy - 1)
    return f"{d.month:02d}/{d.day:02d}"


def _entry_months_to_doys(entry_months_str: str) -> list[int]:
    """
    Convert semicolon-separated month numbers (e.g. "11;12") to a sorted list
    of all calendar DOYs that fall within those months (non-leap year).
    Empty string → all months (DOY 1-365).
    """
    if not entry_months_str.strip():
        return list(range(1, 366))

    months = [int(m.strip()) for m in entry_months_str.split(";") if m.strip()]
    doys: list[int] = []
    for m in sorted(months):
        start = date(_REF_YEAR, m, 1).timetuple().tm_yday
        days  = calendar.monthrange(_REF_YEAR, m)[1]
        doys.extend(range(start, start + days))
    return sorted(doys)


def _build_year_lookup(df: pd.DataFrame) -> dict[int, pd.Series]:
    """
    Build {calendar_year: Series(close, index=day_of_year)} from a stamped
    daily DataFrame.  Multiple rows on the same DOY are resolved to last close.
    """
    lookup: dict[int, pd.Series] = {}
    for year, grp in df.groupby('year'):
        s = grp.groupby('day_of_year')['close'].last()
        lookup[int(year)] = s
    return lookup


def _snap_close(series: pd.Series, target_doy: int, tolerance: int = 5) -> Optional[float]:
    """
    Return the close price at the nearest available trading DOY to target_doy,
    searching within ±tolerance days.  Returns None if nothing found.
    """
    for offset in range(0, tolerance + 1):
        for sign in ([0] if offset == 0 else [1, -1]):
            doy = target_doy + sign * offset
            if doy in series.index:
                return float(series.loc[doy])
    return None


def _max_consec_losses(returns: list[float]) -> int:
    """Longest consecutive streak of non-positive returns."""
    best = streak = 0
    for r in returns:
        streak = streak + 1 if r <= 0 else 0
        best = max(best, streak)
    return best


def _intra_metrics(
    year_series: pd.Series,
    next_year_series: Optional[pd.Series],
    entry_doy: int,
    exit_doy_abs: int,   # absolute DOY, may exceed 365 for cross-year
    entry_close: float,
) -> tuple[float, float, float]:
    """
    Return (mae_pct, mfe_pct, max_drawdown_pct) for a single year-window.

    mae_pct       — Max Adverse Excursion: worst close below entry / entry  (positive value)
    mfe_pct       — Max Favourable Excursion: best close above entry / entry (positive value)
    max_drawdown  — Worst peak-to-trough decline within the window (positive value)
    """
    if exit_doy_abs <= 365:
        mask = (year_series.index >= entry_doy) & (year_series.index <= exit_doy_abs)
        closes = year_series[mask].values
    else:
        exit_doy_wrapped = exit_doy_abs - 365
        part1 = year_series[year_series.index >= entry_doy].values
        part2 = (next_year_series[next_year_series.index <= exit_doy_wrapped].values
                 if next_year_series is not None else np.array([]))
        closes = np.concatenate([part1, part2])

    if len(closes) == 0:
        return 0.0, 0.0, 0.0

    rets_vs_entry = (closes - entry_close) / entry_close * 100
    mae = float(max(0.0, -rets_vs_entry.min()))    # worst adverse  (positive)
    mfe = float(max(0.0,  rets_vs_entry.max()))    # best favourable (positive)

    # Peak-to-trough drawdown
    running_peak = closes[0]
    max_dd = 0.0
    for c in closes:
        running_peak = max(running_peak, c)
        dd = (running_peak - c) / running_peak * 100
        max_dd = max(max_dd, dd)

    return mae, mfe, float(max_dd)


# ── Main scanner ──────────────────────────────────────────────────────────────

def run_best_trade_scan(
    df:                          pd.DataFrame,
    ticker:                      str = "",
    entry_months:                str = "",     # e.g. "11;12"  — empty = all months
    min_days_in_trade:           int = 5,
    max_days_in_trade:           int = 45,
    stop_pct:                    float = 9.0,  # Max Adverse Excursion filter (%)
    min_years:                   int = 15,
    win_rate_threshold:          float = 75.0, # %
    profit_factor_threshold:     float = 1.5,
    max_consec_losses_threshold: int = 999,
    direction:                   str = "long", # "long" | "short"
) -> pd.DataFrame:
    """
    Scan all (entry_doy, exit_doy) pairs within the selected entry months and
    days-in-trade range, using raw daily close prices year-by-year.

    Returns a DataFrame sorted by rank_score (best first) with columns
    matching the Bernstein results table.  Empty DataFrame if no windows pass.
    """
    year_lookup   = _build_year_lookup(df)
    years         = sorted(year_lookup.keys())
    entry_doys    = _entry_months_to_doys(entry_months)
    is_short      = direction.strip().lower() == "short"

    rows: list[dict] = []

    for entry_doy in entry_doys:
        for n_days in range(min_days_in_trade, max_days_in_trade + 1):
            exit_doy_abs     = entry_doy + n_days   # may exceed 365
            cross_year       = exit_doy_abs > 365
            exit_doy_wrapped = exit_doy_abs - 365 if cross_year else exit_doy_abs

            year_returns: list[float] = []
            year_maes:    list[float] = []
            year_mfes:    list[float] = []
            year_dds:     list[float] = []

            for year in years:
                ys        = year_lookup[year]
                next_ys   = year_lookup.get(year + 1) if cross_year else None

                entry_close = _snap_close(ys, entry_doy)
                if cross_year:
                    exit_close = _snap_close(next_ys, exit_doy_wrapped) if next_ys is not None else None
                else:
                    exit_close = _snap_close(ys, exit_doy_wrapped)

                if entry_close is None or exit_close is None or entry_close == 0:
                    continue

                ret = (exit_close - entry_close) / entry_close * 100
                if is_short:
                    ret = -ret

                mae, mfe, dd = _intra_metrics(
                    ys, next_ys, entry_doy, exit_doy_abs, entry_close
                )
                if is_short:
                    mae, mfe = mfe, mae  # flip perspective for shorts

                year_returns.append(ret)
                year_maes.append(mae)
                year_mfes.append(mfe)
                year_dds.append(dd)

            # ── Require minimum observations ──────────────────────────────────
            n_years = len(year_returns)
            if n_years < min_years:
                continue

            # ── Aggregate metrics ─────────────────────────────────────────────
            pos_rets = [r for r in year_returns if r > 0]
            neg_rets = [r for r in year_returns if r <= 0]

            wins     = len(pos_rets)
            win_rate = wins / n_years * 100

            avg_profit = float(np.mean(pos_rets)) if pos_rets else 0.0
            avg_loss   = float(np.mean(neg_rets)) if neg_rets else 0.0

            gross_profit = sum(pos_rets)
            gross_loss   = abs(sum(neg_rets))
            profit_factor = (gross_profit / gross_loss
                             if gross_loss > 0 else 999.0)

            max_win  = float(max(year_returns))
            max_loss = float(min(year_returns))
            max_mae  = float(max(year_maes))    # worst adverse excursion
            max_mfe  = float(max(year_mfes))    # best favourable excursion
            max_dd   = float(max(year_dds))     # worst peak-to-trough

            growth       = float(sum(year_returns))
            max_consec   = _max_consec_losses(year_returns)

            # Ratio of average profit magnitude to average loss magnitude
            pct_avg_profit = (avg_profit / abs(avg_loss) * 100
                              if avg_loss != 0 else 999.0)
            pct_avg_loss   = (abs(avg_loss) / avg_profit * 100
                              if avg_profit != 0 else 999.0)

            # ── Apply filters ─────────────────────────────────────────────────
            if win_rate       < win_rate_threshold:          continue
            if profit_factor  < profit_factor_threshold:     continue
            if max_mae        > stop_pct:                    continue
            if max_consec     > max_consec_losses_threshold: continue

            # ── Rank score ────────────────────────────────────────────────────
            rank_score = (win_rate * profit_factor) / (1 + max_mae / 100)

            rows.append({
                # Identity
                'sym':               ticker,
                'l_s':               'S' if is_short else 'L',
                'entry_date':        _doy_to_mmdd(entry_doy),
                'exit_date':         _doy_to_mmdd(exit_doy_wrapped),
                # Window geometry
                'entry_doy':         entry_doy,
                'exit_doy':          exit_doy_wrapped,
                'days_in_trade':     n_days,
                # Search params (informational)
                'stop_pct':          round(stop_pct, 1),
                # Core metrics — matches Bernstein results_output.png column order
                'pl_ratio':          round(profit_factor, 2),
                'pct_win':           round(win_rate, 1),
                'wins':              wins,
                'n_years':           n_years,
                'avg_profit':        round(avg_profit, 2),
                'avg_loss':          round(avg_loss, 2),
                'pct_avg_profit':    round(pct_avg_profit, 2),
                'pct_avg_loss':      round(pct_avg_loss, 2),
                'max_win':           round(max_win, 2),
                'max_loss':          round(max_loss, 2),
                'max_up_swing':      round(max_mfe, 2),
                'max_stop':          round(max_mae, 2),
                'max_drawdown':      round(max_dd, 2),
                'growth':            round(growth, 2),
                # Extra diagnostics
                'max_consec_losses': max_consec,
                'rank_score':        round(rank_score, 4),
            })

    if not rows:
        return pd.DataFrame()

    result = (pd.DataFrame(rows)
              .sort_values('rank_score', ascending=False)
              .reset_index(drop=True))
    return result


# ── Chart ─────────────────────────────────────────────────────────────────────

def draw_top_trades_chart(
    trades_df: pd.DataFrame,
    ticker:    str,
    top_n:     int = 20,
) -> mpl_figure.Figure:
    """
    Horizontal bar chart of top N trade windows sorted by rank_score (best at top).
    Bar length = win rate %, colour = green/amber/red by threshold.
    """
    df  = trades_df.head(top_n).copy().iloc[::-1].reset_index(drop=True)
    n   = len(df)

    labels = [
        f"{row.entry_date} → {row.exit_date}  ({int(row.days_in_trade)}d)"
        for _, row in df.iterrows()
    ]
    win_rates = df['pct_win'].values
    colors    = [GREEN if w >= 75 else (AMBER if w >= 60 else RED)
                 for w in win_rates]

    fig, ax = plt.subplots(figsize=FIGURE_FIGSIZE)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    ax.barh(range(n), win_rates, color=colors, alpha=0.85, height=0.6)

    for i, (_, row) in enumerate(df.iterrows()):
        annotation = (
            f"PL:{row.pl_ratio:.1f}  "
            f"+{row.avg_profit:.1f}% / {row.avg_loss:.1f}%  "
            f"growth:{row.growth:.1f}%  "
            f"yrs:{int(row.n_years)}"
        )
        ax.text(row.pct_win + 1, i, annotation,
                va='center', fontsize=7, color='#333333')

    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Win Rate %', fontsize=9)
    ax.set_xlim(0, 130)
    ax.set_ylim(-0.6, n - 0.4)

    # Reference line at threshold
    ax.axvline(x=75, color=GRAY, linewidth=0.8, linestyle='--', alpha=0.6)
    ax.text(75.5, -0.5, '75%', fontsize=7, color=GRAY, va='bottom')

    ax.set_title(
        f'BEST SEASONAL TRADES   {ticker}   Top {n}',
        fontsize=11, fontweight='bold', pad=10,
        fontfamily='monospace',
    )

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.xaxis.grid(True, color='#eeeeee', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.tick_params(axis='both', length=0, labelsize=8)

    plt.tight_layout()
    return fig
