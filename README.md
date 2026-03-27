# Seasonality Bernstein

Two independent programs driven entirely by CSV input files.

---

## The Two Phases

| | Phase 1 | Phase 2 |
|---|---|---|
| **Script** | `bernstein_cli.py` | `best_trade_cli.py` |
| **Purpose** | Generate seasonal charts (PNG) | Find best seasonal trade windows |
| **Output** | PNG images | Ranked CSV of trade windows |
| **Run independently** | Yes | Yes |

They share nothing at runtime. You run only what you need.

---

## Phase 1 — Chart Generation

```bash
python bernstein_cli.py user_input/jobs/recreate_nvda_old.csv
python bernstein_cli.py user_input/jobs/ndx100_standard_charts.csv --workers 4
```

### Chart types

| `chart_type` | Short alias | Description |
|---|---|---|
| `Calendar Day (1-31)` | `calendar_day` | Return by calendar day of month |
| `Trading Day (1-22)` | `trading_day` | Return by trading day of month |
| `Weekly Payroll (W1-5)` | `weekly_payroll` | Payroll week effect |
| `Weekday Effect` | `weekday_effect` | Mon–Fri patterns |
| `Monthly (Jan-Dec)` | `monthly` | Calendar month seasonality |
| `Quarterly Halves` | `quarterly` | 8 half-quarters |
| `Annual Window` | `annual_window` | Custom date window (e.g. Oct15–Dec31) |
| `Grouping of Days` | `grouping` | Custom day-range groups |
| `Seasonal Run` | `seasonal_run` | Consecutive reliable periods |
| `Best/Worst Periods` | `best_worst` | Top N best/worst periods |
| `Bernstein Composite` | `composite` | **New** — weekly 0–100 normalized line, green/red + ↑ arrows |

### Input CSV columns (Phase 1)

| Column | Required | Default | Description |
|---|---|---|---|
| `job_id` | Yes | — | Output filename prefix |
| `ticker` | One of | — | Single ticker, e.g. `SPY` |
| `ticker_file` | One of | — | Path to ticker list → expands to one job per ticker |
| `chart_type` | Yes | — | See table above |
| `start_year` | No | all | First year to include |
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
| `win_rate_arrow_threshold` | No | `65.0` | (Bernstein Composite only) % win rate to draw ↑ arrow |
| `output_path` | No | `output/` | Output directory |

### Multi-ticker — how it works

Set `ticker_file` instead of `ticker` in any row. The batch processor reads the file
and creates **one job per ticker** using the same chart settings from that row.
Multiple rows = multiple chart types, each expanded to the full ticker list.

```csv
# 3 rows × 101 tickers = 303 jobs automatically
job_id,          ticker, ticker_file,                     chart_type,         ...
monthly_wr,            , tickers/nasdaq100_tickers.csv,  Monthly (Jan-Dec),  ...
calendar_ab,           , tickers/nasdaq100_tickers.csv,  Calendar Day (1-31),...
quarterly_cagr,        , tickers/nasdaq100_tickers.csv,  Quarterly Halves,   ...
```

```bash
python bernstein_cli.py user_input/jobs/ndx100_standard_charts.csv --workers 4
```

---

## Phase 2 — Best Trade Scanner

### What it does

Scans every possible (entry date, exit date) combination within the months you
select and ranks the windows by how consistently they worked historically.
Uses **raw daily close prices year-by-year** — completely independent of the
Bernstein Composite chart.  Each calendar year is one observation per window.

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
| `entry_months` | all | Months to scan for entry dates. `11;12` = Nov+Dec only. Empty = all 12 months |
| `min_days_in_trade` | `5` | Shortest window allowed (calendar days) |
| `max_days_in_trade` | `45` | Longest window allowed (calendar days) |
| `stop_pct` | `9.0` | **Max Adverse Excursion filter** — exclude windows where the worst intra-trade drop exceeded this % |
| `min_years` | `15` | Minimum number of years with valid data required before reporting a window |
| `win_rate_threshold` | `75.0` | Minimum % of years that must have been profitable |
| `profit_factor_threshold` | `1.50` | Minimum F/L ratio (gross profit ÷ gross loss) |
| `max_consec_losses` | `999` | Maximum allowed consecutive losing years (999 = filter off) |
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

| Column | What it means | Example |
|---|---|---|
| `sym` | Ticker symbol | `AA` |
| `l_s` | Long or Short | `L` |
| `entry_date` | Entry date (MM/DD) — buy at close | `11/21` = Nov 21 |
| `exit_date` | Exit date (MM/DD) — sell at close | `11/28` = Nov 28 |
| `entry_doy` | Entry as day-of-year (1–365) | `325` |
| `exit_doy` | Exit as day-of-year (1–365) | `332` |
| `days_in_trade` | Window length in calendar days | `7` |
| `stop_pct` | The MAE filter used in this scan | `9.0` |
| `pl_ratio` | **Profit Factor** — gross profit ÷ gross loss. 20.6 means for every $1 lost you made $20.60. >1.5 is good, >3 is strong | `20.59` |
| `pct_win` | **Win Rate %** — how often this window was profitable across all years | `76.9%` |
| `wins` | Count of profitable years | `20` |
| `n_years` | Total years with valid data | `26` |
| `avg_profit` | Average return on winning years (%) | `+6.39%` |
| `avg_loss` | Average return on losing years (%) | `-1.03%` |
| `pct_avg_profit` | avg_profit ÷ avg_loss × 100 — how much bigger wins are vs losses | `617.75` |
| `pct_avg_loss` | avg_loss ÷ avg_profit × 100 — inverse ratio | `16.19` |
| `max_win` | Best single-year return (%) | `+57.08%` |
| `max_loss` | Worst single-year return (%) | `-3.58%` |
| `max_up_swing` | **Max Favourable Excursion** — best intra-trade close vs entry across all years (%) | `52.99%` |
| `max_stop` | **Max Adverse Excursion** — worst intra-trade close vs entry across all years (%). This is the most you could have been down before exit | `6.23%` |
| `max_drawdown` | Worst peak-to-trough decline within the window across all years (%) | `6.23%` |
| `growth` | **Cumulative growth** — sum of all annual returns over the full lookback. The total % return if you traded this window every single year | `121.58%` |
| `max_consec_losses` | Longest streak of consecutive losing years | `3` |
| `rank_score` | Internal sort key: `(win_rate × pl_ratio) / (1 + max_stop/100)`. Higher = better | `1491.07` |

**How to read a row:** The top AA result says — buying AA on Nov 21 and selling Nov 28 (a 7-day window) has worked in 20 out of 26 years (76.9%). When it wins, you average +6.4%; when it loses, you average only -1.0%. The worst it ever went against you mid-trade was -6.2%. If you had traded this every year since 2000, your cumulative gain would be +121.6%.

---

### Understanding the bar chart (`aa_bt_top20_chart.png`)

Each bar is one trade window, sorted best-first (top = highest rank score).

- **Bar length** = Win Rate % (longer = more consistent)
- **Colour** = green ≥75% win rate, amber 60–74%, red <60%
- **Label on right** = `PL:<profit_factor>  +<avg_profit>% / <avg_loss>%  growth:<cumulative>%  yrs:<n_years>`
- **Dashed vertical line** = 75% win rate reference

The best trades appear at the top with long green bars and high PL ratios.

---

## Directory Layout

```
seasonality_Bernstein/
├── bernstein_cli.py          ← Phase 1 entry point
├── best_trade_cli.py         ← Phase 2 entry point
├── requirements.txt
├── README.md
│
├── user_input/
│   ├── jobs/                 ← CSVs you actually run
│   │   ├── recreate_nvda_old.csv
│   │   ├── ndx100_standard_charts.csv
│   │   ├── best_trade_spy.csv
│   │   └── best_trade_ndx100.csv
│   ├── templates/            ← Copy & edit to create your own jobs
│   │   ├── BLANK.csv         ← All columns, no data rows
│   │   └── EXAMPLES.csv      ← One example per chart type
│   ├── tickers/              ← Ticker list files
│   │   ├── nasdaq100_tickers.csv
│   │   ├── sp500_tickers.csv
│   │   ├── russell3000_tickers.csv
│   │   └── iwm1000_tickers.csv
│   └── archive/              ← Old cycles-dashboard format files (not compatible)
│
├── output/                   ← Generated charts and CSVs (auto-created)
│   └── old/                  ← Reference NVDA charts from previous run
│
├── src/
│   ├── data/data_loader.py   ← yfinance + CSV loading (cached 24h)
│   └── core/
│       ├── stamper.py           ← Adds temporal columns to price data
│       ├── bernstein_config.py  ← Config dataclass + CSV parser
│       ├── bernstein_result.py  ← Result container (matplotlib only)
│       ├── engine.py            ← Job router (Phase 1)
│       ├── batch.py             ← Sequential/parallel batch runner
│       ├── bernstein_chart.py   ← Bernstein weekly composite chart
│       └── best_trade.py        ← Best Trade DOY scanner + chart
│
└── data/cache/               ← yfinance cache (auto-created, 24h TTL)
```

---

## Naming convention for output files

| Suffix in `job_id` | Meaning |
|---|---|
| `_ab` | Average Return + **B**ands (`show_bands=true`) |
| `_ar` | Average Return + **R**eliability (`show_reliability=true`) |
| `_cagr` | Y-axis = Annualized CAGR |
| `_wr` | Y-axis = **W**in **R**ate |

---

## Caching

Yahoo Finance data is cached in `data/cache/` for 24 hours.
Delete files there to force a fresh download.
