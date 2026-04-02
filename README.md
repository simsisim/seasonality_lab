# Seasonality Lab

Two independent programs driven entirely by CSV input files.

---

## The Two Phases

| | Phase 1 | Phase 2 |
|---|---|---|
| **Script** | `seasonality_cli.py` | `best_trade_cli.py` |
| **Purpose** | Generate seasonal charts (PNG) | Find best seasonal trade windows |
| **Output** | PNG images | Ranked CSV of trade windows |
| **Run independently** | Yes | Yes |

They share nothing at runtime. You run only what you need.

---

## Phase 1 — Chart Generation

```bash
python seasonality_cli.py user_input/jobs/recreate_nvda_old.csv
python seasonality_cli.py user_input/jobs/ndx100_standard_charts.csv --workers 4
```

### Chart types

| `chart_type` | Short alias | Description |
|---|---|---|
| `Calendar Day (1-31)` | `calendar_day` | Return by calendar day of month |
| `Trading Day (1-22)` | `trading_day` | Return by trading day of month |
| `Weekly Payroll (W1-5)` | `weekly_payroll` | Payroll week effect |
| `Weekday Effect` | `weekday_effect` | Mon–Fri patterns |
| `Monthly (Jan-Dec)` | `monthly` | Calendar month seasonality |
| `Quarterly Halves` | `quarterly` | Each quarter split into 2 halves (split day configurable) |
| `Annual Window` | `annual_window` | Custom date window (e.g. Oct15–Dec31) |
| `Grouping of Days` | `grouping` | Month split into day-range groups (fully configurable) |
| `Seasonal Run` | `seasonal_run` | Consecutive reliable periods |
| `Best/Worst Periods` | `best_worst` | Top N best/worst periods |
| `Bernstein Composite` | `composite` | Weekly 0–100 normalized line, green/red + ↑ arrows |

### Input CSV columns (Phase 1)

| Column | Required | Default | Description |
|---|---|---|---|
| `job_id` | Yes | — | Output filename prefix |
| `ticker` | One of | — | Single ticker, e.g. `SPY` |
| `ticker_file` | One of | — | Path to ticker list → expands to one job per ticker |
| `chart_type` | Yes | — | See table above |
| `start_year` | No | all history | First year to include (blank = max available) |
| `end_year` | No | latest | Last year to include |
| `exclude_years` | No | none | Semicolon-separated years to skip, e.g. `2008;2020` |
| `aggregation` | No | `Simple Average` | `Simple Average` \| `Median` \| `Weighted Average` |
| `data_type` | No | `Returns` | `Returns` \| `Prices` \| `Log Returns` |
| `normalization` | No | `None` | `None` \| `Start=100` \| `Scale 0-100` \| `Z-Score` \| `Winsorize` |
| `detrend_enabled` | No | `false` | `true` \| `false` |
| `detrend_method` | No | `Linear` | `Linear` \| `Mean` |
| `alignment` | No | `None` | `None` \| `Majority Rule` \| `Weekday-Week` |
| `logic_calc` | No | `average_daily` | `average_daily` \| `open_close_month` \| `open_close_period` |
| `y_axis_metric` | No | `Average Return` | `Average Return` \| `Win Rate` \| `Cumulative Return` \| `Annualized (CAGR)` \| `Annualized (Bowley 252x)` |
| `show_bands` | No | `false` | Show min/max range band |
| `show_reliability` | No | `false` | Highlight consecutive high-win-rate runs |
| `smoothing_period` | No | `1` | Moving average window (1 = off) |
| `day_groups` | No | `1-6,7-12,13-18,19-25,26-31` | **Grouping of Days only** — comma-separated day ranges, e.g. `1-10,11-20,21-31` |
| `quarter_split_day` | No | `15` | **Quarterly Halves only** — day-of-month to split each quarter |
| `win_rate_arrow_threshold` | No | `65.0` | **Bernstein Composite only** — % win rate to draw ↑ arrow |
| `output_path` | No | `output/` | Output directory |

### Chart subtitle — what is shown

Every chart shows a subtitle line below the title. It always includes:
- `hist_yr = N` — number of distinct historical years used in the calculation

When `show_reliability = true` it also includes:
- `★★★ = Strong (WR≥65%, n≥30)  |  ★★ = Reliable (WR≥59%, n≥20)  |  ★ = Limited  |  Faded bars = low sample size`

### Grouping of Days — configuration

The month is divided into day-range groups. Default is 5 groups:

| Group | Days |
|---|---|
| G1 | 1–6 |
| G2 | 7–12 |
| G3 | 13–18 |
| G4 | 19–25 |
| G5 | 26–31 |

To use different groups, set `day_groups` in the job CSV:
```csv
# 3-group classic split
day_groups = 1-10,11-20,21-31

# 6-group fine split
day_groups = 1-5,6-10,11-15,16-20,21-25,26-31
```

### Quarterly Halves — configuration

Each quarter is split into two halves at a configurable day of the middle month.
Default `quarter_split_day = 15`:

| Period | Range |
|---|---|
| Q1 (1st) | Jan 1 – Feb 15 |
| Q1 (2nd) | Feb 16 – Mar 31 |
| Q2 (1st) | Apr 1 – May 15 |
| Q2 (2nd) | May 16 – Jun 30 |
| Q3 (1st) | Jul 1 – Aug 15 |
| Q3 (2nd) | Aug 16 – Sep 30 |
| Q4 (1st) | Oct 1 – Nov 15 |
| Q4 (2nd) | Nov 16 – Dec 31 |

To shift the split: set `quarter_split_day = 10` (or any day 1–27) in the job CSV.

### Multi-ticker — how it works

Set `ticker_file` instead of `ticker` in any row. The batch processor reads the file
and creates **one job per ticker** using the same chart settings from that row.

```csv
# 3 rows × 101 tickers = 303 jobs automatically
job_id,          ticker, ticker_file,                     chart_type,         ...
monthly_wr,            , tickers/nasdaq100_tickers.csv,  Monthly (Jan-Dec),  ...
calendar_ab,           , tickers/nasdaq100_tickers.csv,  Calendar Day (1-31),...
quarterly_cagr,        , tickers/nasdaq100_tickers.csv,  Quarterly Halves,   ...
```

```bash
python seasonality_cli.py user_input/jobs/ndx100_standard_charts.csv --workers 4
```

---

## Data Sources

### Ticker file format

Ticker files use a two-column format: `TICKER[,source]`

```
# Format: TICKER[,source]
# source: yf | stooq | local  (blank = auto)
SPY,
QQQ,
^DJI,local
AAPL,yf
```

| `source` value | Behaviour |
|---|---|
| *(blank)* / `auto` | Check `hist_data/` first → fall back to Yahoo Finance |
| `yf` | Yahoo Finance only |
| `stooq` | Read from `hist_data/` (Stooq data, manually downloaded — see below) |
| `local` | `hist_data/` only — hard error if file not found |

### hist_data — long-history local files

For tickers where Yahoo Finance history is insufficient (e.g. DJIA back to 1896),
place a manually downloaded CSV in:

```
user_input/tickers/hist_data/{TICKER}.csv
```

Required columns: `Date, Open, High, Low, Close, Volume` (any case, Date as `YYYY-MM-DD`).

**Example — DJIA full history from Stooq:**
1. Go to `https://stooq.com/q/d/?s=^dji`, select range **Max**, format **CSV**, download
2. Save as `user_input/tickers/hist_data/^DJI.csv`
3. Set ticker file entry to `^DJI,local` (or `^DJI,stooq`)

The filename must match the ticker symbol exactly (`^DJI.csv` for ticker `^DJI`).

### Data source in job CSV

The `data_source` column in job CSV files accepts the same values (`yf`, `stooq`, `local`, `auto`).
When using `ticker_file`, the **per-ticker source in the ticker file takes precedence**.

### Caching

Yahoo Finance downloads are cached in `data/cache/` for 24 hours.
Cache filename format: `YFI_{SYMBOL}_{interval}_{start}_{end}.csv`
Delete files there to force a fresh download.

---

## Phase 2 — Best Trade Scanner

### What it does

Scans every possible (entry date, exit date) combination within the months you
select and ranks the windows by how consistently they worked historically.
Uses **raw daily close prices year-by-year** — completely independent of the
Bernstein Composite chart. Each calendar year is one observation per window.

### How to create a job file

Copy the template and edit:
```
user_input/templates/best_trade_batch.csv
```

Or use an existing example:
```
user_input/jobs/best_trade_aa.csv   ← Alcoa, Nov+Dec entries
user_input/jobs/best_trade_spy.csv  ← SPY, Nov+Dec entries
```

### How to run

```bash
# Basic run
python best_trade_cli.py user_input/jobs/best_trade_aa.csv

# Skip the chart, CSV only
python best_trade_cli.py user_input/jobs/best_trade_aa.csv --no-chart

# Multi-ticker batch, 4 parallel workers
python best_trade_cli.py user_input/jobs/best_trade_ndx100.csv --workers 4
```

### Output files

```
output/best_trade/
├── aa_bt_best_trades.csv      ← all qualifying windows, best-first
└── aa_bt_top20_chart.png      ← horizontal bar chart of top 20
```

---

### Input CSV columns (Phase 2)

| Column | Default | Description |
|---|---|---|
| `job_id` | — | Output filename prefix |
| `ticker` / `ticker_file` | — | Single ticker or path to ticker list |
| `start_year` | all | First year of historical data to use |
| `end_year` | today | Last year |
| `exclude_years` | none | Semicolon-separated years to skip, e.g. `2008;2020` |
| `entry_months` | all | Months to scan for entry dates. `11;12` = Nov+Dec only |
| `min_days_in_trade` | `5` | Shortest window allowed (calendar days) |
| `max_days_in_trade` | `45` | Longest window allowed (calendar days) |
| `stop_pct` | `9.0` | Max Adverse Excursion filter — exclude windows where intra-trade drop exceeded this % |
| `min_years` | `15` | Minimum years with valid data required before reporting a window |
| `win_rate_threshold` | `75.0` | Minimum % of years that must have been profitable |
| `profit_factor_threshold` | `1.50` | Minimum profit factor (gross profit ÷ gross loss) |
| `max_consec_losses` | `999` | Maximum allowed consecutive losing years (999 = off) |
| `direction` | `long` | `long` or `short` |
| `top_n` | `20` | Number of trades shown in the chart |
| `save_chart` | `true` | Whether to save the PNG chart |
| `output_path` | `output/best_trade/` | Output directory |

**Key parameters to tune:**

- Widen results → lower `win_rate_threshold` (e.g. 70) or `profit_factor_threshold` (e.g. 1.2)
- Stricter results → raise `win_rate_threshold` (e.g. 80) or lower `stop_pct` (e.g. 5)
- Different season → change `entry_months` (e.g. `"1;2"` for Jan+Feb, `"10;11;12"` for Q4)
- Longer trades → raise `max_days_in_trade` (e.g. 90)

---

### Understanding the output CSV

**Example row from `aa_bt_best_trades.csv`:**

```
sym  l_s  entry_date  exit_date  days_in_trade  pct_win  pl_ratio  avg_profit  avg_loss  growth  max_stop  rank_score
AA   L    11/21       11/28      7              76.9     20.59     6.39        -1.03     121.58  6.23      1491.07
```

| Column | What it means |
|---|---|
| `sym` | Ticker symbol |
| `l_s` | Long or Short |
| `entry_date` | Entry date (MM/DD) — buy at close |
| `exit_date` | Exit date (MM/DD) — sell at close |
| `days_in_trade` | Window length in calendar days |
| `pl_ratio` | **Profit Factor** — gross profit ÷ gross loss. >1.5 good, >3 strong |
| `pct_win` | **Win Rate %** — how often profitable across all years |
| `wins` / `n_years` | Profitable years / total years with data |
| `avg_profit` / `avg_loss` | Average return on winning / losing years |
| `max_win` / `max_loss` | Best / worst single-year return |
| `max_up_swing` | Max Favourable Excursion — best intra-trade close vs entry |
| `max_stop` | **Max Adverse Excursion** — worst intra-trade close vs entry (how far it went against you) |
| `growth` | **Cumulative growth** — sum of all annual returns over the full lookback |
| `max_consec_losses` | Longest streak of consecutive losing years |
| `rank_score` | Sort key: `(win_rate × pl_ratio) / (1 + max_stop/100)` |

---

### Understanding the bar chart

Each bar is one trade window, sorted best-first (top = highest rank score).

- **Bar length** = Win Rate % (longer = more consistent)
- **Colour** = green ≥75% win rate, amber 60–74%, red <60%
- **Label on right** = `PL:<profit_factor>  +<avg_profit>% / <avg_loss>%  growth:<cumulative>%  yrs:<n_years>`
- **Dashed vertical line** = 75% win rate reference

---

## Directory Layout

```
seasonality_lab/
├── seasonality_cli.py            ← Phase 1 entry point
├── best_trade_cli.py             ← Phase 2 entry point
├── requirements.txt
├── README.md
│
├── user_input/
│   ├── jobs/                     ← CSVs you actually run
│   ├── templates/                ← Copy & edit to create your own jobs
│   │   ├── BLANK.csv             ← All columns, no data rows
│   │   └── EXAMPLES.csv          ← One example per chart type
│   └── tickers/                  ← Ticker list files
│       ├── nasdaq100_tickers.csv
│       ├── sp500_tickers.csv
│       ├── russell3000_tickers.csv
│       ├── iwm1000_tickers.csv
│       └── hist_data/            ← Manually saved long-history CSVs
│           └── ^DJI.csv          ← DJIA from 1896 (downloaded from Stooq)
│
├── output/                       ← Generated charts and CSVs (auto-created)
│
├── src/
│   ├── data/data_loader.py       ← YF + Stooq (local) + hist_data loading (cached 24h)
│   └── core/
│       ├── stamper.py            ← Adds temporal columns to price data
│       ├── bernstein_config.py   ← Config dataclass + CSV parser
│       ├── bernstein_result.py   ← Result container
│       ├── engine.py             ← Job router (Phase 1)
│       ├── batch.py              ← Sequential/parallel batch runner
│       ├── bernstein_chart.py    ← Bernstein weekly composite chart
│       ├── legacy_charts.py      ← All other chart types
│       └── best_trade.py         ← Best Trade DOY scanner + chart
│
└── data/cache/                   ← Download cache (auto-created, 24h TTL)
```

---

## Naming convention for output files

| Suffix in `job_id` | Meaning |
|---|---|
| `_ab` | Average Return + **B**ands (`show_bands=true`) |
| `_ar` | Average Return + **R**eliability (`show_reliability=true`) |
| `_cagr` | Y-axis = Annualized CAGR |
| `_wr` | Y-axis = **W**in **R**ate |
