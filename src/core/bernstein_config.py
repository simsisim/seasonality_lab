"""
BernsteinJobConfig — comprehensive configuration for all chart types.

Supports all chart types shown in the UI (Calendar Day, Trading Day, Monthly, etc.)
plus the two new Bernstein-specific modes (Composite, Best Trade).

CSV batch columns reference:
    job_id, ticker, ticker_file, chart_type,
    start_year, end_year, exclude_years,
    data_source, interval,
    aggregation, data_type, normalization,
    detrend_enabled, detrend_method,
    alignment, logic_calc, y_axis_metric,
    show_bands, show_reliability, smoothing_period,
    win_rate_arrow_threshold,
    min_years, win_rate_threshold, profit_factor_threshold, max_dd_threshold,
    output_path, notes
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import csv
from pathlib import Path


# ── Figure size constants (single source of truth for all chart types) ────────
FIGURE_FIGSIZE = (14.0, 6.0)   # inches (width × height)
FIGURE_DPI     = 150            # savefig DPI → 2100 × 900 px output


# ── Chart type constants ──────────────────────────────────────────────────────
# Legacy seasonal chart types (maintained from cycles-dashboard)
CHART_CALENDAR_DAY    = "Calendar Day (1-31)"
CHART_TRADING_DAY     = "Trading Day (1-22)"
CHART_WEEKLY_PAYROLL  = "Weekly Payroll (W1-5)"
CHART_WEEKDAY_EFFECT  = "Weekday Effect"
CHART_MONTHLY         = "Monthly (Jan-Dec)"
CHART_QUARTERLY       = "Quarterly Halves"
CHART_ANNUAL_WINDOW   = "Annual Window"
CHART_GROUPING        = "Grouping of Days"
CHART_SEASONAL_RUN    = "Seasonal Run"
CHART_BEST_WORST      = "Best/Worst Periods"

# New Bernstein-specific chart types
CHART_BERNSTEIN       = "Bernstein Composite"   # Weekly 0-100 normalized composite
CHART_BEST_TRADE      = "Best Trade"             # Exhaustive DOY window scanner

ALL_CHART_TYPES = [
    CHART_CALENDAR_DAY, CHART_TRADING_DAY, CHART_WEEKLY_PAYROLL,
    CHART_WEEKDAY_EFFECT, CHART_MONTHLY, CHART_QUARTERLY,
    CHART_ANNUAL_WINDOW, CHART_GROUPING, CHART_SEASONAL_RUN,
    CHART_BEST_WORST, CHART_BERNSTEIN, CHART_BEST_TRADE,
]

# Short aliases accepted in CSV (case-insensitive)
_CHART_ALIASES = {
    "calendar_day": CHART_CALENDAR_DAY,
    "calendar day": CHART_CALENDAR_DAY,
    "trading_day": CHART_TRADING_DAY,
    "trading day": CHART_TRADING_DAY,
    "weekly_payroll": CHART_WEEKLY_PAYROLL,
    "weekday_effect": CHART_WEEKDAY_EFFECT,
    "weekday effect": CHART_WEEKDAY_EFFECT,
    "monthly": CHART_MONTHLY,
    "quarterly": CHART_QUARTERLY,
    "quarterly_halves": CHART_QUARTERLY,
    "annual_window": CHART_ANNUAL_WINDOW,
    "grouping": CHART_GROUPING,
    "grouping_of_days": CHART_GROUPING,
    "seasonal_run": CHART_SEASONAL_RUN,
    "best_worst": CHART_BEST_WORST,
    "bernstein": CHART_BERNSTEIN,
    "bernstein_composite": CHART_BERNSTEIN,
    "composite": CHART_BERNSTEIN,
    "best_trade": CHART_BEST_TRADE,
}


def _resolve_chart_type(raw: str) -> str:
    """Normalise chart_type from CSV to canonical constant."""
    stripped = raw.strip()
    # Try exact match first
    for ct in ALL_CHART_TYPES:
        if stripped.lower() == ct.lower():
            return ct
    # Try alias
    alias = _CHART_ALIASES.get(stripped.lower())
    if alias:
        return alias
    raise ValueError(
        f"Unknown chart_type '{stripped}'. Valid types:\n  " +
        "\n  ".join(ALL_CHART_TYPES)
    )


# ── Y-axis metric constants ───────────────────────────────────────────────────
METRIC_AVG_RETURN   = "Average Return"
METRIC_WIN_RATE     = "Win Rate"
METRIC_CUMULATIVE   = "Cumulative Return"
METRIC_CAGR         = "Annualized (CAGR)"
METRIC_BOWLEY       = "Annualized (Bowley 252x)"

# ── Alignment constants ───────────────────────────────────────────────────────
ALIGN_NONE           = "None"
ALIGN_MAJORITY_RULE  = "Majority Rule"
ALIGN_WEEKDAY_WEEK   = "Weekday-Week"

# ── Logic calc constants ──────────────────────────────────────────────────────
CALC_AVERAGE_DAILY   = "average_daily"
CALC_OPEN_CLOSE_MTH  = "open_close_month"
CALC_OPEN_CLOSE_PER  = "open_close_period"


@dataclass
class BernsteinJobConfig:
    # ── Identity ───────────────────────────────────────────────────────────────
    job_id: str = ""

    # ── Ticker input (use ticker OR ticker_file, not both) ────────────────────
    ticker: str = ""
    ticker_file: str = ""          # Path to a text file with one ticker per line

    # ── Chart type ─────────────────────────────────────────────────────────────
    chart_type: str = CHART_MONTHLY

    # ── Data loading ───────────────────────────────────────────────────────────
    data_source: str = "yahoo"     # "yahoo" | "csv" | "market_data"
    interval: str = "1d"           # "1d" | "1wk" | "1mo"

    # ── Date scope ─────────────────────────────────────────────────────────────
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    exclude_years: Optional[str] = None   # semicolon-separated, e.g. "2008;2020"

    # ── Calculation (all configurable per screenshot) ──────────────────────────
    aggregation: str = "Simple Average"   # Simple Average | Median | Weighted Average
    data_type: str = "Returns"            # Returns | Prices | Log Returns
    normalization: str = "None"           # None | Start=100 | Scale 0-100 | Z-Score | Winsorize
    detrend_enabled: bool = False
    detrend_method: str = "Linear"        # Linear | Mean

    # ── Alignment / Logic ──────────────────────────────────────────────────────
    alignment: str = ALIGN_NONE           # None | Majority Rule | Weekday-Week
    logic_calc: str = CALC_AVERAGE_DAILY  # average_daily | open_close_month | open_close_period

    # ── Y-axis metric ──────────────────────────────────────────────────────────
    y_axis_metric: str = METRIC_AVG_RETURN

    # ── Chart display options ──────────────────────────────────────────────────
    show_bands: bool = False       # Show min/max band around average line
    show_reliability: bool = False # Highlight high win-rate seasonal runs
    smoothing_period: int = 1      # 1 = no smoothing, 3/5/7 = SMA window

    # ── Bernstein Composite options (chart_type = "Bernstein Composite") ───────
    win_rate_arrow_threshold: float = 65.0   # weeks to mark with ↑ arrow

    # ── Grouping of Days options ───────────────────────────────────────────────
    day_groups: Optional[str] = None    # e.g. "1-6,7-12,13-18,19-25,26-31"

    # ── Quarterly Halves options ───────────────────────────────────────────────
    quarter_split_day: Optional[int] = None  # day-of-month to split each quarter (default 15)

    # ── Best Trade scanner options (chart_type = "Best Trade") ────────────────
    min_years: int = 15
    win_rate_threshold: float = 0.70
    profit_factor_threshold: float = 1.5
    max_dd_threshold: float = 0.20

    # ── Output ─────────────────────────────────────────────────────────────────
    output_path: str = "output/"
    notes: str = ""

    # ── Derived helpers ────────────────────────────────────────────────────────
    @property
    def excluded_years_list(self) -> list[int]:
        if not self.exclude_years:
            return []
        return [int(y.strip()) for y in self.exclude_years.split(";") if y.strip()]

    @property
    def is_bernstein_mode(self) -> bool:
        return self.chart_type in (CHART_BERNSTEIN, CHART_BEST_TRADE)


# ── CSV batch loader ──────────────────────────────────────────────────────────

def _to_bool(v: str) -> bool:
    return v.strip().lower() in {"true", "yes", "1"}

def _parse_int(v: str, default=None) -> Optional[int]:
    v = v.strip()
    return int(v) if v else default

def _parse_float(v: str, default: float = 0.0) -> float:
    v = v.strip()
    return float(v) if v else default


def _parse_row(row: dict) -> BernsteinJobConfig:
    """Build one BernsteinJobConfig from a CSV row dict (keys already lowercased)."""
    chart_type_raw = row.get("chart_type", CHART_MONTHLY)
    chart_type = _resolve_chart_type(chart_type_raw) if chart_type_raw.strip() else CHART_MONTHLY

    return BernsteinJobConfig(
        job_id           = row.get("job_id", ""),
        ticker           = row.get("ticker", "").upper().strip(),
        ticker_file      = row.get("ticker_file", "").strip(),
        chart_type       = chart_type,
        data_source      = row.get("data_source", "yahoo").lower().strip(),
        interval         = row.get("interval", "1d").strip(),
        start_year       = _parse_int(row.get("start_year", "")),
        end_year         = _parse_int(row.get("end_year", "")),
        exclude_years    = row.get("exclude_years", "").strip(),
        aggregation      = row.get("aggregation", "Simple Average").strip() or "Simple Average",
        data_type        = row.get("data_type", "Returns").strip() or "Returns",
        normalization    = row.get("normalization", "None").strip() or "None",
        detrend_enabled  = _to_bool(row.get("detrend_enabled", "false")),
        detrend_method   = row.get("detrend_method", "Linear").strip() or "Linear",
        alignment        = row.get("alignment", ALIGN_NONE).strip() or ALIGN_NONE,
        logic_calc       = row.get("logic_calc", CALC_AVERAGE_DAILY).strip() or CALC_AVERAGE_DAILY,
        y_axis_metric    = row.get("y_axis_metric", METRIC_AVG_RETURN).strip() or METRIC_AVG_RETURN,
        show_bands       = _to_bool(row.get("show_bands", "false")),
        show_reliability = _to_bool(row.get("show_reliability", "false")),
        smoothing_period = int(_parse_float(row.get("smoothing_period", ""), 1)),
        day_groups                = row.get("day_groups", "").strip() or None,
        quarter_split_day         = _parse_int(row.get("quarter_split_day", "")),
        win_rate_arrow_threshold  = _parse_float(row.get("win_rate_arrow_threshold", ""), 65.0),
        min_years                 = int(_parse_float(row.get("min_years", ""), 15)),
        win_rate_threshold        = _parse_float(row.get("win_rate_threshold", ""), 0.70),
        profit_factor_threshold   = _parse_float(row.get("profit_factor_threshold", ""), 1.5),
        max_dd_threshold          = _parse_float(row.get("max_dd_threshold", ""), 0.20),
        output_path      = row.get("output_path", "output/").strip() or "output/",
        notes            = row.get("notes", "").strip(),
    )


def _expand_ticker_file(cfg: BernsteinJobConfig, base_dir: Path) -> list[BernsteinJobConfig]:
    """
    If ticker_file is set, read tickers from that file and return one config per ticker.
    The job_id is suffixed with the ticker symbol: {job_id}_{TICKER}.
    """
    ticker_path = Path(cfg.ticker_file)
    if not ticker_path.is_absolute():
        ticker_path = base_dir / ticker_path

    if not ticker_path.exists():
        raise FileNotFoundError(f"ticker_file not found: {ticker_path}")

    # Parse (ticker, optional_source) pairs from the ticker file.
    # Format: one entry per line, optionally "TICKER,source"
    # Valid sources: yf, stooq, local  (blank = auto)
    ticker_entries: list[tuple[str, str]] = []
    for line in ticker_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.lower() in ("ticker", "ticker,source"):
            continue
        parts = line.rstrip(",").split(",", 1)
        ticker = parts[0].strip().upper()
        source = parts[1].strip().lower() if len(parts) > 1 else ""
        if ticker:
            ticker_entries.append((ticker, source))

    import copy
    configs = []
    for ticker, source in ticker_entries:
        c = copy.copy(cfg)
        c.ticker = ticker
        c.ticker_file = ""
        c.job_id = f"{cfg.job_id}_{ticker}" if cfg.job_id else ticker
        # Column 2 source overrides the job-level data_source only when specified
        if source:
            c.data_source = source
        configs.append(c)

    return configs


def load_batch_csv(csv_path: str) -> list[BernsteinJobConfig]:
    """
    Parse a batch CSV file and return a list of BernsteinJobConfig objects.

    - Lines starting with '#' and blank lines are skipped.
    - Column matching is case-insensitive.
    - If a row has ticker_file set, it is expanded into one config per ticker.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Batch CSV not found: {csv_path}")

    base_dir = path.parent
    configs: list[BernsteinJobConfig] = []

    with open(path, newline="", encoding="utf-8") as f:
        lines = [l for l in f if not l.strip().lstrip('"').startswith("#") and l.strip()]

    reader = csv.DictReader(lines)

    for row in reader:
        row = {k.strip().lower().replace(" ", "_"): (v or "").strip()
               for k, v in row.items() if k is not None}
        cfg = _parse_row(row)

        if cfg.ticker_file:
            configs.extend(_expand_ticker_file(cfg, base_dir))
        elif cfg.ticker:
            configs.append(cfg)
        else:
            raise ValueError(f"Row '{cfg.job_id}' has neither 'ticker' nor 'ticker_file'")

    return configs
