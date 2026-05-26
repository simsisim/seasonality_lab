"""
legacy_charts.py — Matplotlib implementations of standard seasonal chart types.

Generates matplotlib Figure objects saved via fig.savefig() — no kaleido needed.

Chart types:
  Calendar Day (1-31), Trading Day (1-22), Weekday Effect,
  Monthly (Jan-Dec), Quarterly Halves (8 periods), Grouping of Days

Features:
  - Value % labels on top of each bar
  - Win % labels below the zero line (green ≥60%, red ≤40%, gray otherwise)
  - Dotted horizontal average line with annotation
  - ★/★★/★★★ confidence tiers when show_reliability=True
  - Faded bars for low sample size (always on)
  - ± 1 std-dev error bars when show_bands=True (year-level std, not raw daily)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.figure as mpl_figure

from .bernstein_config import BernsteinJobConfig, FIGURE_FIGSIZE, FIGURE_DPI

# ── Reliability threshold ─────────────────────────────────────────────────────
RELIABILITY_THRESHOLD = 59.0

# ── Style ─────────────────────────────────────────────────────────────────────
PLOT_BG     = '#e8eef4'    # light blue-gray plot area
TITLE_COLOR = '#1f2937'    # dark navy (matches old Plotly default template)
AXIS_COLOR  = '#444444'
GRID_COLOR  = 'white'

# ── Bar base colors (R, G, B) in 0-255 ───────────────────────────────────────
_GREEN_RGB = (0,   200,  83)
_RED_RGB   = (244,  67,  54)
_GRAY_RGB  = (158, 158, 158)

MONTH_NAMES  = ['Jan','Feb','Mar','Apr','May','Jun',
                'Jul','Aug','Sep','Oct','Nov','Dec']
MONTH_ABBR_1 = ['','Jan','Feb','Mar','Apr','May','Jun',
                'Jul','Aug','Sep','Oct','Nov','Dec']   # 1-indexed

# ── Quarterly Halves date ranges ──────────────────────────────────────────────
# Default split day (day-of-month of the middle month of each quarter).
# Override per-job via config.quarter_split_day.
_QUARTER_SPLIT_DAY_DEFAULT = 15

# Quarter definitions: (label_prefix, q_start_month, q_end_month, q_end_day)
_QUARTER_DEFS = [
    ('Q1',  1,  3, 31),
    ('Q2',  4,  6, 30),
    ('Q3',  7,  9, 30),
    ('Q4', 10, 12, 31),
]


def _build_quarterly_halves(split_day: int) -> list:
    """
    Build the 8 quarterly-half period definitions for a given split day.

    Each quarter is split at `split_day` of its middle month:
      1st half: month1/1  → month2/split_day
      2nd half: month2/(split_day+1) → month3/end_day

    Returns list of (label, start_month, start_day, end_month, end_day).
    """
    halves = []
    for prefix, qm1, qm3, qm3_end in _QUARTER_DEFS:
        qm2 = qm1 + 1          # middle month of the quarter
        halves.append((f'{prefix} (1st)', qm1,  1,   qm2, split_day))
        halves.append((f'{prefix} (2nd)', qm2,  split_day + 1, qm3, qm3_end))
    return halves


# =============================================================================
# STATISTICS  (unchanged — pure pandas/numpy, no rendering)
# =============================================================================

def _daily_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add daily_return column from close pct_change (%)."""
    df = df.copy()
    df['daily_return'] = df['close'].pct_change() * 100.0
    return df[np.isfinite(df['daily_return'])]


def calculate_stats(group_data: pd.DataFrame, value_col: str = 'daily_return') -> Dict:
    """
    Compute per-period statistics.
    Ported from cycles-dashboard/seasonality_charts.py::calculate_stats.
    """
    values = group_data[value_col].dropna()
    if len(values) == 0:
        return {
            'mean': 0.0, 'std': 0.0, 'win_rate': 0.0, 'count': 0,
            'cumulative': 0.0, 'annualized': 0.0, 'compound_252': 0.0, 'bowley': 0.0,
            'is_reliable': False, 'p25': 0.0, 'p75': 0.0,
        }

    win_rate  = float((values > 0).mean() * 100)
    mean_val  = float(values.mean())
    std_val   = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    cumul     = float(values.sum())

    compound = 1.0
    for r in values:
        compound *= (1.0 + r / 100.0)

    if 'year' in group_data.columns:
        yrs = group_data['year'].dropna()
        yr_span = float(yrs.max() - yrs.min() + 1) if len(yrs) > 0 else float(len(values)) / 12.0
    else:
        yr_span = float(len(values)) / 12.0

    if yr_span > 0 and compound > 0 and np.isfinite(compound):
        try:
            annualized = (compound ** (1.0 / yr_span) - 1.0) * 100.0
            if not np.isfinite(annualized):
                annualized = float("nan")
        except (OverflowError, ValueError):
            annualized = float("nan")
    else:
        annualized = 0.0

    try:
        compound_252 = ((1.0 + mean_val / 100.0) ** 252 - 1.0) * 100.0 if mean_val != 0 else 0.0
        if not np.isfinite(compound_252):
            compound_252 = float("nan")
    except (OverflowError, ValueError):
        compound_252 = float("nan")
    bowley       = mean_val * 253.0

    return {
        'mean':         mean_val,
        'std':          std_val,
        'win_rate':     win_rate,
        'count':        int(len(values)),
        'cumulative':   cumul,
        'annualized':   annualized,
        'compound_252': compound_252,
        'bowley':       bowley,
        'is_reliable':  win_rate >= RELIABILITY_THRESHOLD,
        'p25':          float(values.quantile(0.25)),
        'p75':          float(values.quantile(0.75)),
    }


def _empty_stats() -> Dict:
    return {
        'mean': 0.0, 'std': 0.0, 'win_rate': 0.0, 'count': 0,
        'cumulative': 0.0, 'annualized': 0.0, 'compound_252': 0.0, 'bowley': 0.0,
        'is_reliable': False, 'p25': 0.0, 'p75': 0.0,
    }


def _year_std(df: pd.DataFrame, group_col: str, value_col: str) -> pd.Series:
    """Std dev of per-year means per period group — for show_bands."""
    ym = df.groupby(['year', group_col])[value_col].mean()
    return ym.groupby(level=group_col).std(ddof=1).fillna(0.0)


# =============================================================================
# RELIABILITY HELPERS
# =============================================================================

def get_reliability_tier(win_rate: float, count: int) -> str:
    """★★★ = Strong | ★★ = Reliable | ★ = Limited | '' = unreliable."""
    if win_rate >= 65 and count >= 30:
        return '★★★'
    elif win_rate >= 59 and count >= 20:
        return '★★'
    elif win_rate >= 59:
        return '★'
    return ''


def get_sample_size_opacity(count: int) -> float:
    if count >= 30: return 1.0
    if count >= 20: return 0.75
    if count >= 10: return 0.5
    return 0.3


# =============================================================================
# COLOR HELPERS  (matplotlib RGBA tuples, values 0-1)
# =============================================================================

def _mpl_color(rgb_255: tuple, alpha: float) -> tuple:
    return (rgb_255[0] / 255.0, rgb_255[1] / 255.0, rgb_255[2] / 255.0, alpha)


def _bar_colors_mpl(stats_list: List[Dict]) -> List[tuple]:
    """Green/gray/red by win rate + opacity by sample size → matplotlib RGBA."""
    colors = []
    for s in stats_list:
        wr = s.get('win_rate', 50)
        if wr >= 60:
            rgb, base_alpha = _GREEN_RGB, 0.85
        elif wr <= 40:
            rgb, base_alpha = _RED_RGB,   0.85
        else:
            rgb, base_alpha = _GRAY_RGB,  0.60
        opacity = base_alpha * get_sample_size_opacity(s.get('count', 30))
        colors.append(_mpl_color(rgb, opacity))
    return colors


# =============================================================================
# OPEN-CLOSE PERIOD CALCULATIONS  (unchanged)
# =============================================================================

def calculate_open_close_month(df: pd.DataFrame, group_col: str = 'month') -> pd.DataFrame:
    """One period return per (year, period): first-open → last-close."""
    open_col  = next((c for c in df.columns if c.lower() == 'open'),  None)
    close_col = next((c for c in df.columns if c.lower() == 'close'), None)
    day_col   = next((c for c in df.columns if c.lower() in ('day', 'calendar_day')), None)

    if not all([open_col, close_col, day_col, 'year' in df.columns, group_col in df.columns]):
        return pd.DataFrame()

    results = []
    for (year, period), grp in df.groupby(['year', group_col]):
        grp_s = grp.sort_values(day_col)
        fo = grp_s.iloc[0][open_col]
        lc = grp_s.iloc[-1][close_col]
        if pd.notna(fo) and pd.notna(lc) and fo != 0:
            results.append({group_col: period, 'year': year,
                             'period_return': (lc - fo) / fo * 100.0})
    return pd.DataFrame(results) if results else pd.DataFrame()


def calculate_open_close_date_ranges(df: pd.DataFrame,
                                     date_ranges: List[Tuple]) -> pd.DataFrame:
    """Period returns for date-range-based periods (e.g. Quarterly Halves)."""
    open_col  = next((c for c in df.columns if c.lower() == 'open'),  None)
    close_col = next((c for c in df.columns if c.lower() == 'close'), None)
    day_col   = next((c for c in df.columns if c.lower() in ('day', 'calendar_day')), None)

    empty = pd.DataFrame(columns=['period_label', 'year', 'period_return'])
    if not all([open_col, close_col, day_col]):
        return empty
    if 'year' not in df.columns or 'month' not in df.columns:
        return empty

    results = []
    for label, sm, sd, em, ed in date_ranges:
        for year in sorted(df['year'].unique()):
            if sm > em:
                continue
            mask = (
                (df['year'] == year) & (
                    ((df['month'] == sm) & (df[day_col] >= sd)) |
                    ((df['month'] > sm) & (df['month'] < em)) |
                    ((df['month'] == em) & (df[day_col] <= ed))
                )
            )
            pdata = df[mask].sort_values(['month', day_col])
            if len(pdata) == 0:
                continue
            fo = pdata.iloc[0][open_col]
            lc = pdata.iloc[-1][close_col]
            if pd.notna(fo) and pd.notna(lc) and fo != 0:
                results.append({'period_label': label, 'year': year,
                                 'period_return': (lc - fo) / fo * 100.0})
    return pd.DataFrame(results) if results else empty


# =============================================================================
# Y-AXIS SELECTION  (unchanged)
# =============================================================================

def _select_y_axis(stats_list: List[Dict], y_axis_metric: str,
                   ticker: str = '') -> Tuple[List, List[str], List[str], str]:
    """
    Returns (y_values, top_labels, bottom_labels, yaxis_title).
    top_labels   = shown on bars (the primary metric)
    bottom_labels= shown below bars (the context metric)
    """
    m = y_axis_metric

    if 'Win Rate' in m:
        y    = [s['win_rate']           for s in stats_list]
        tops = [f"{v:.0f}%"             if not np.isnan(v) else '' for v in y]
        bots = [f"{s['mean']:.2f}%"     for s in stats_list]
        ytit = (f"% of time {ticker} closed higher" if ticker else "Win Rate (%)")
    elif 'CAGR' in m or ('Annualized' in m and 'Bowley' not in m):
        y    = [s['annualized']          for s in stats_list]
        tops = [f"{v:.1f}%"              if not np.isnan(v) else '' for v in y]
        bots = [f"{s['win_rate']:.0f}%"  for s in stats_list]
        ytit = "Annualized Return % (CAGR)"
    elif 'Bowley' in m or '252' in m:
        y    = [s['bowley']              for s in stats_list]
        tops = [f"{v:.1f}%"              if not np.isnan(v) else '' for v in y]
        bots = [f"{s['win_rate']:.0f}%"  for s in stats_list]
        ytit = "Annualized Return % (Bowley 252×)"
    elif 'Cumul' in m:
        y    = [s['cumulative']          for s in stats_list]
        tops = [f"{v:.1f}%"              if not np.isnan(v) else '' for v in y]
        bots = [f"{s['win_rate']:.0f}%"  for s in stats_list]
        ytit = "Cumulative Return (%)"
    else:  # Average Return (default)
        y    = [s['mean']                for s in stats_list]
        tops = [f"{v:.2f}%"              if not np.isnan(v) else '' for v in y]
        bots = [f"{s['win_rate']:.0f}%"  for s in stats_list]
        ytit = "Average Return (%)"

    return y, tops, bots, ytit


# =============================================================================
# MATPLOTLIB RENDERING HELPERS
# =============================================================================

def _build_title(chart_name: str, config: BernsteinJobConfig, n_years: int = 0) -> Tuple[str, str]:
    """Returns (main_title, subtitle). subtitle is '' when show_reliability=False."""
    yr  = f"{config.start_year or ''}–{config.end_year or 'present'}"
    main = f"Average Performance by {chart_name} | {config.ticker}, {yr}"
    hist_part = f"hist_yr = {n_years}" if n_years else ""
    sub  = ""
    if config.show_reliability:
        sub = ("★★★ = Strong (WR≥65%, n≥30)  |  ★★ = Reliable (WR≥59%, n≥20)  |"
               "  ★ = Limited  |  Faded bars = low sample size")
        if hist_part:
            sub += f"  |  {hist_part}"
    elif hist_part:
        sub = hist_part
    return main, sub


def _apply_layout_mpl(fig: mpl_figure.Figure, ax: plt.Axes,
                      main_title: str, subtitle: str,
                      xaxis_title: str, yaxis_title: str) -> None:
    """Apply consistent style: background, grid, spines, titles, tick params."""
    fig.patch.set_facecolor('white')
    ax.set_facecolor(PLOT_BG)

    # Hide all spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # White horizontal grid only, drawn behind bars
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.9, zorder=0)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    # Tick params — no tick marks, just labels
    ax.tick_params(axis='both', which='both', length=0,
                   colors=AXIS_COLOR, labelsize=9)

    # Axis labels
    ax.set_xlabel(xaxis_title, fontsize=11, color=TITLE_COLOR, labelpad=6)
    ax.set_ylabel(yaxis_title, fontsize=11, color=TITLE_COLOR, labelpad=6)

    # Titles — placed in figure coordinates so they sit above the axes
    has_sub = bool(subtitle)
    fig.text(0.5, 0.97, main_title, ha='center', va='top',
             fontsize=13, color=TITLE_COLOR, transform=fig.transFigure)
    if has_sub:
        fig.text(0.5, 0.91, subtitle, ha='center', va='top',
                 fontsize=8, color='#555555', transform=fig.transFigure)

    top_margin = 0.85 if has_sub else 0.90
    fig.subplots_adjust(top=top_margin, bottom=0.13, left=0.08, right=0.96)


def _add_average_line_mpl(ax: plt.Axes, y_values: List) -> None:
    """Dotted black average line + right-aligned annotation."""
    clean = [float(v) for v in y_values if v is not None and np.isfinite(float(v))]
    if not clean:
        return
    avg = float(np.mean(clean))
    ax.axhline(y=avg, color='black', linewidth=1.5, linestyle=':', zorder=5)
    # get_yaxis_transform: x in axes [0,1], y in data units — perfect for right-edge label
    ax.text(0.99, avg, f"Average = {avg:.2f}%",
            transform=ax.get_yaxis_transform(),
            ha='right', va='bottom',
            fontsize=9, color='black', zorder=6)


def _add_bar_value_labels(ax: plt.Axes, x_pos: np.ndarray,
                          y_values: List, top_labels: List[str],
                          y_range: float, std_bands: List[float]) -> None:
    """Value labels just above (positive) or below (negative) the bar edge."""
    pad = max(y_range * 0.015, 1e-6)
    for i, (xp, yv, label) in enumerate(zip(x_pos, y_values, top_labels)):
        if not label or not np.isfinite(float(yv)):
            continue
        # Place at bar edge only — do not offset by error bar size
        if float(yv) >= 0:
            ax.text(xp, float(yv) + pad, label,
                    ha='center', va='bottom', fontsize=9, color='#333333', zorder=6)
        else:
            ax.text(xp, float(yv) - pad, label,
                    ha='center', va='top', fontsize=9, color='#333333', zorder=6)


def _add_bottom_labels_mpl(ax: plt.Axes, x_pos: np.ndarray,
                            texts: List[str], win_rates: List[float],
                            label_y: float) -> None:
    """Win% / avg-return labels just below the zero line."""
    for xp, text, wr in zip(x_pos, texts, win_rates):
        if not text or text in ('0%', '0.00%'):
            continue
        color = '#00c853' if wr >= 60 else ('#f44336' if wr <= 40 else '#666666')
        ax.text(xp, label_y, text,
                ha='center', va='top', fontsize=9, color=color, zorder=6)


def _add_reliability_annotations_mpl(ax: plt.Axes, stats_list: List[Dict],
                                      x_pos: np.ndarray, y_values: List,
                                      std_bands: List[float], y_range: float) -> None:
    """★/★★/★★★ gold stars positioned above bar tops."""
    pad = max(y_range * 0.04, 1e-6)
    for i, (s, xp, yv) in enumerate(zip(stats_list, x_pos, y_values)):
        tier = get_reliability_tier(s['win_rate'], s['count'])
        if not tier:
            continue
        eb  = std_bands[i] if std_bands else 0.0
        top = max(float(yv), 0.0) + eb + pad
        ax.text(xp, top, tier,
                ha='center', va='bottom', fontsize=12, color='gold', zorder=6)


# =============================================================================
# CORE BAR CHART RENDERER
# =============================================================================

def _draw_bar_chart(
    x_values:    List,
    stats_list:  List[Dict],
    std_bands:   List[float],
    config:      BernsteinJobConfig,
    chart_name:  str,
    xaxis_title: str,
    n_years:     int = 0,
) -> mpl_figure.Figure:
    """
    Core bar chart renderer for all legacy chart types.
    Returns a matplotlib Figure.
    """
    y_values, top_labels, bot_labels, yaxis_title = _select_y_axis(
        stats_list, config.y_axis_metric, config.ticker
    )
    colors  = _bar_colors_mpl(stats_list)
    x_pos   = np.arange(len(x_values))
    n_bars  = len(x_values)

    # ── Y range for layout ────────────────────────────────────────────────────
    y_vals_clean = [float(v) for v in y_values if np.isfinite(float(v))]
    y_max_v = max(y_vals_clean) if y_vals_clean else 1.0
    y_min_v = min(y_vals_clean) if y_vals_clean else 0.0
    y_range = max(abs(y_max_v - y_min_v), 1e-6)

    # Extra vertical space: top for labels+error bars, bottom for win-rate labels
    clean_eb = [float(v) for v in std_bands if np.isfinite(float(v))]
    max_eb   = max(clean_eb) if (config.show_bands and any(v > 0 for v in clean_eb)) else 0.0
    y_top   = y_max_v + max_eb + y_range * 0.20
    y_bot   = min(y_min_v, 0.0) - y_range * 0.18   # room for win-rate labels
    label_y = min(y_min_v, 0.0) - y_range * 0.07   # y position of win-rate text

    # ── Create figure ─────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=FIGURE_FIGSIZE)

    # ── Bars ──────────────────────────────────────────────────────────────────
    yerr = ([float(v) if np.isfinite(float(v)) else 0.0 for v in std_bands]
            if config.show_bands and any(v > 0 for v in clean_eb) else None)
    ax.bar(
        x_pos, y_values,
        color=colors,
        width=0.72,
        yerr=yerr,
        error_kw=dict(ecolor=(0.4, 0.4, 0.4, 0.45), capsize=2, linewidth=1.2),
        zorder=3,
    )

    # ── Y limits ──────────────────────────────────────────────────────────────
    ax.set_ylim(y_bot, y_top)

    # ── X-axis tick labels ────────────────────────────────────────────────────
    # Replace <br> (Plotly HTML) with newline for multi-line labels
    tick_labels = [str(x).replace('<br>', '\n') for x in x_values]
    ax.set_xticks(x_pos)
    tick_fs = 8 if n_bars > 20 else 9
    ax.set_xticklabels(tick_labels, fontsize=tick_fs)

    # ── Zero line ─────────────────────────────────────────────────────────────
    ax.axhline(y=0, color=(0, 0, 0, 0.35), linewidth=0.8, zorder=2)

    # ── Average line + annotation ─────────────────────────────────────────────
    _add_average_line_mpl(ax, y_values)

    # ── Value labels above/below bars ─────────────────────────────────────────
    _add_bar_value_labels(ax, x_pos, y_values, top_labels, y_range,
                          std_bands if config.show_bands else [0.0] * n_bars)

    # ── Win-rate / context labels below zero line ─────────────────────────────
    win_rates = [s['win_rate'] for s in stats_list]
    _add_bottom_labels_mpl(ax, x_pos, bot_labels, win_rates, label_y)

    # ── Reliability stars ─────────────────────────────────────────────────────
    if config.show_reliability:
        _add_reliability_annotations_mpl(
            ax, stats_list, x_pos, y_values,
            std_bands if config.show_bands else [0.0] * n_bars,
            y_range,
        )

    # ── Layout, style, titles ─────────────────────────────────────────────────
    main_title, subtitle = _build_title(chart_name, config, n_years)
    _apply_layout_mpl(fig, ax, main_title, subtitle, xaxis_title, yaxis_title)

    return fig


# =============================================================================
# STATISTICS COMPUTATION  (one function per chart type — unchanged)
# =============================================================================

def _stats_calendar_day(df: pd.DataFrame, config: BernsteinJobConfig
                        ) -> Tuple[List[Dict], List, List[float]]:
    df = _daily_returns(df)
    stats_list, std_bands, x = [], [], list(range(1, 32))
    for day in range(1, 32):
        grp   = df[df['day'] == day]
        stats = calculate_stats(grp, 'daily_return')
        stats_list.append(stats)
        if config.show_bands and len(grp) > 1 and 'year' in grp.columns:
            ym = grp.groupby('year')['daily_return'].mean()
            std_bands.append(float(ym.std(ddof=1)) if len(ym) > 1 else 0.0)
        else:
            std_bands.append(0.0)
    return stats_list, x, std_bands


def _stats_trading_day(df: pd.DataFrame, config: BernsteinJobConfig
                       ) -> Tuple[List[Dict], List, List[float]]:
    df = _daily_returns(df)
    stats_list, std_bands, x = [], [], list(range(1, 23))
    for td in range(1, 23):
        grp   = df[df['trading_day_of_month'] == td]
        stats = calculate_stats(grp, 'daily_return')
        stats_list.append(stats)
        if config.show_bands and len(grp) > 1 and 'year' in grp.columns:
            ym = grp.groupby('year')['daily_return'].mean()
            std_bands.append(float(ym.std(ddof=1)) if len(ym) > 1 else 0.0)
        else:
            std_bands.append(0.0)
    return stats_list, x, std_bands


def _stats_weekday(df: pd.DataFrame, config: BernsteinJobConfig
                   ) -> Tuple[List[Dict], List, List[float]]:
    df = _daily_returns(df)
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    stats_list, std_bands = [], []
    for dow in range(0, 5):
        grp   = df[df['day_of_week'] == dow]
        stats = calculate_stats(grp, 'daily_return')
        stats_list.append(stats)
        if config.show_bands and len(grp) > 1 and 'year' in grp.columns:
            ym = grp.groupby('year')['daily_return'].mean()
            std_bands.append(float(ym.std(ddof=1)) if len(ym) > 1 else 0.0)
        else:
            std_bands.append(0.0)
    return stats_list, day_names, std_bands


def _stats_monthly(df: pd.DataFrame, config: BernsteinJobConfig
                   ) -> Tuple[List[Dict], List, List[float]]:
    stats_list, std_bands = [], []

    if config.logic_calc == 'open_close_month':
        monthly_df = calculate_open_close_month(df, 'month')
        if monthly_df.empty:
            return _stats_monthly_avg_daily(df, config)
        for m in range(1, 13):
            mret = monthly_df[monthly_df['month'] == m]
            if len(mret) > 0:
                tmp   = pd.DataFrame({'period_return': mret['period_return'].values,
                                      'year':         mret['year'].values})
                stats = calculate_stats(tmp, 'period_return')
            else:
                stats = _empty_stats()
            stats_list.append(stats)
            std_bands.append(stats['std'])
    else:
        return _stats_monthly_avg_daily(df, config)

    return stats_list, MONTH_NAMES, std_bands


def _stats_monthly_avg_daily(df: pd.DataFrame, config: BernsteinJobConfig
                              ) -> Tuple[List[Dict], List, List[float]]:
    df = _daily_returns(df)
    stats_list, std_bands = [], []
    for m in range(1, 13):
        grp   = df[df['month'] == m]
        stats = calculate_stats(grp, 'daily_return')
        stats_list.append(stats)
        if config.show_bands and len(grp) > 1 and 'year' in grp.columns:
            ym = grp.groupby('year')['daily_return'].mean()
            std_bands.append(float(ym.std(ddof=1)) if len(ym) > 1 else 0.0)
        else:
            std_bands.append(stats['std'])
    return stats_list, MONTH_NAMES, std_bands


def _stats_quarterly(df: pd.DataFrame, config: BernsteinJobConfig
                     ) -> Tuple[List[Dict], List, List[float]]:
    split_day = config.quarter_split_day or _QUARTER_SPLIT_DAY_DEFAULT
    quarterly_halves = _build_quarterly_halves(split_day)

    stats_list, std_bands, x_labels = [], [], []

    if config.logic_calc == 'open_close_period':
        period_df = calculate_open_close_date_ranges(df, quarterly_halves)
        for label, sm, sd, em, ed in quarterly_halves:
            date_range = f"{MONTH_ABBR_1[sm]} {sd} - {MONTH_ABBR_1[em]} {ed}"
            x_labels.append(f"{label}\n{date_range}")
            if len(period_df) > 0 and 'period_label' in period_df.columns:
                pdata = period_df[period_df['period_label'] == label]
                if len(pdata) > 0:
                    tmp   = pd.DataFrame({'period_return': pdata['period_return'].values,
                                          'year':         pdata['year'].values})
                    stats = calculate_stats(tmp, 'period_return')
                    std_bands.append(stats['std'])
                else:
                    stats = _empty_stats()
                    std_bands.append(0.0)
            else:
                stats = _empty_stats()
                std_bands.append(0.0)
            stats_list.append(stats)
    else:
        df = _daily_returns(df)
        for label, sm, sd, em, ed in quarterly_halves:
            date_range = f"{MONTH_ABBR_1[sm]} {sd} - {MONTH_ABBR_1[em]} {ed}"
            x_labels.append(f"{label}\n{date_range}")
            mask = (
                ((df['month'] == sm) & (df['day'] >= sd)) |
                ((df['month'] > sm) & (df['month'] < em)) |
                ((df['month'] == em) & (df['day'] <= ed))
            )
            grp   = df[mask]
            stats = calculate_stats(grp, 'daily_return')
            stats_list.append(stats)
            if config.show_bands and len(grp) > 1 and 'year' in grp.columns:
                ym = grp.groupby('year')['daily_return'].mean()
                std_bands.append(float(ym.std(ddof=1)) if len(ym) > 1 else 0.0)
            else:
                std_bands.append(stats['std'])

    return stats_list, x_labels, std_bands


_DAY_GROUPS_DEFAULT = '1-6,7-12,13-18,19-25,26-31'


def _parse_day_groups(spec: str) -> List[Tuple[str, range]]:
    """
    Parse a day_groups spec string into (label, range) pairs.
    Format: "1-6,7-12,13-18,19-25,26-31"
    """
    groups = []
    for i, part in enumerate(spec.split(','), start=1):
        part = part.strip()
        if '-' not in part:
            raise ValueError(f"Invalid day_groups segment '{part}': expected 'start-end'")
        start_s, end_s = part.split('-', 1)
        start, end = int(start_s.strip()), int(end_s.strip())
        groups.append((f'G{i}: {start}-{end}', range(start, end + 1)))
    return groups


def _stats_grouping(df: pd.DataFrame, config: BernsteinJobConfig
                    ) -> Tuple[List[Dict], List, List[float]]:
    df = _daily_returns(df)
    spec = config.day_groups or _DAY_GROUPS_DEFAULT
    groups = _parse_day_groups(spec)

    stats_list, std_bands, x_labels = [], [], []
    for label, days in groups:
        x_labels.append(label)
        grp   = df[df['day'].isin(days)]
        stats = calculate_stats(grp, 'daily_return')
        stats_list.append(stats)
        if config.show_bands and len(grp) > 1 and 'year' in grp.columns:
            ym = grp.groupby('year')['daily_return'].mean()
            std_bands.append(float(ym.std(ddof=1)) if len(ym) > 1 else 0.0)
        else:
            std_bands.append(stats['std'])
    return stats_list, x_labels, std_bands


# =============================================================================
# ROUTER + ENTRY POINT
# =============================================================================

_STATS_FN: Dict = {
    'Calendar Day (1-31)': (_stats_calendar_day,  'Calendar Day (1-31)', 'Day of Month'),
    'Trading Day (1-22)':  (_stats_trading_day,   'Trading Day (1-22)',  'Trading Day of Month'),
    'Weekday Effect':      (_stats_weekday,        'Weekday Effect',      'Day of Week'),
    'Monthly (Jan-Dec)':   (_stats_monthly,        'Monthly (Jan-Dec)',   'Month'),
    'Quarterly Halves':    (_stats_quarterly,      'Quarterly Halves',    'Quarter Half'),
    'Grouping of Days':    (_stats_grouping,       'Grouping of Days',    'Day Group'),
}


def generate_legacy_chart(
    df: pd.DataFrame,
    config: BernsteinJobConfig,
) -> Tuple[mpl_figure.Figure, pd.DataFrame]:
    """
    Main entry point for all legacy chart types.

    Returns:
        (fig, stats_df) — matplotlib Figure + tabular stats for CSV export.
    """
    chart_type = config.chart_type
    entry = _STATS_FN.get(chart_type)
    if entry is None:
        raise NotImplementedError(
            f"Chart type '{chart_type}' not implemented. "
            f"Available: {list(_STATS_FN.keys())}"
        )
    stats_fn, chart_name, xaxis_title = entry

    stats_list, x_labels, std_bands = stats_fn(df, config)

    n_years = df['year'].nunique() if 'year' in df.columns else 0

    fig = _draw_bar_chart(
        x_values    = x_labels,
        stats_list  = stats_list,
        std_bands   = std_bands,
        config      = config,
        chart_name  = chart_name,
        xaxis_title = xaxis_title,
        n_years     = n_years,
    )

    # Build export DataFrame
    y_values, _, _, _ = _select_y_axis(stats_list, config.y_axis_metric, config.ticker)
    stats_df = pd.DataFrame({
        'period':        [str(x) for x in x_labels],
        'mean':          [s['mean']         for s in stats_list],
        'win_rate':      [s['win_rate']      for s in stats_list],
        'count':         [s['count']         for s in stats_list],
        'annualized':    [s['annualized']    for s in stats_list],
        'bowley':        [s['bowley']        for s in stats_list],
        'cumulative':    [s['cumulative']    for s in stats_list],
        'std':           [s['std']           for s in stats_list],
        'selected_value':[v                  for v in y_values],
    })

    return fig, stats_df
