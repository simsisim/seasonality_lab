# Usage Overview

Four CLI tools, run in order from broad to specific:

```
seasonality_cli.py   →  Step 0: generate/refresh all seasonal charts and stats
summary_cli.py       →  Step 1: once/year — best 1/2/3-month windows per ticker → CSV
screener_cli.py      →  Step 2: anytime — top tickers for the next 1-3 months
best_trade_cli.py    →  Step 3: per ticker — best entry/exit day within a month
```

---

## tv_convert.py — TradingView watchlist converter

Converts a TradingView watchlist export (`.txt`) to a standard ticker CSV
that all other tools can read. Runs automatically inside the GitHub Actions
workflow — you never need to run it manually.

```bash
# Convert (output: same filename with .csv extension)
python tv_convert.py user_input/tickers/Ioa_port.txt

# Custom output path
python tv_convert.py user_input/tickers/Ioa_port.txt -o user_input/tickers/Ioa_port.csv

# Include non-US exchanges (GETTEX, TRADEGATE, etc.)
python tv_convert.py user_input/tickers/Ioa_port.txt --all-exchanges
```

| Flag | Default | Description |
|------|---------|-------------|
| `--output` / `-o` | same path, `.csv` extension | Output CSV path |
| `--all-exchanges` | off | Include non-US tickers (skipped by default) |

**Where to save watchlist files:** `user_input/tickers/`

**Workflow integration:** tick *Custom watchlist* in the GitHub Actions UI — the workflow
runs `tv_convert.py` automatically before `seasonality_cli.py`, so you only need to
commit an updated `.txt` file.

---

## seasonality_cli.py — Chart & stats generation

Generates seasonal charts and stats CSVs for all tickers. Run once per year
(or after adding new tickers). Input is a job CSV from `user_input/jobs/`.

```bash
# Generate charts + stats for all SP500 tickers
python seasonality_cli.py user_input/jobs/sp500_standard_charts.csv

# NDX100
python seasonality_cli.py user_input/jobs/ndx100_standard_charts.csv

# IWM1000 / Russell3000 (slow — use workers)
python seasonality_cli.py user_input/jobs/iwm1000_standard_charts.csv --workers 4
python seasonality_cli.py user_input/jobs/russell3000_standard_charts.csv --workers 4

# Custom output directory
python seasonality_cli.py user_input/jobs/sp500_standard_charts.csv -o output/sp500/

# Suppress progress output
python seasonality_cli.py user_input/jobs/sp500_standard_charts.csv --quiet
```

| Flag | Default | Description |
|------|---------|-------------|
| `--output` / `-o` | per-job config | Override output directory |
| `--workers` / `-w` | `1` | Parallel workers |
| `--quiet` / `-q` | off | Suppress progress output |

---

## summary_cli.py — Best windows reference (run once/year)

For every ticker computes the best 1-month, 2-month and 3-month consecutive
seasonal windows across the full year. No filters — every ticker gets a row.
Open the output CSV in Excel and sort by any column.

```bash
# All indices at once (recommended)
python summary_cli.py

# Single index
python summary_cli.py --index sp500
python summary_cli.py --index ndx100

# Custom output directory
python summary_cli.py --index all -o output/summary/
```

| Flag | Default | Description |
|------|---------|-------------|
| `--index` / `-i` | `all` | `sp500`, `ndx100`, `iwm1000`, `russell3000`, `all` |
| `--output` / `-o` | `output/summary/` | Output directory |

**Output:** `output/summary/{index}_best_windows.csv` — one row per ticker with
columns `best_1m`, `1m_wr%`, `1m_ret%`, `1m_score`, `best_2m` … `3m_score`.

---

## screener_cli.py — Seasonal top-performer screener

Ranks tickers by seasonal quality for a specific month window. Answers:
*"What are the best seasonal trades for the next 1-3 months?"*

```bash
# Auto-detects next 2 months from today
python screener_cli.py

# Explicit months, multiple indices
python screener_cli.py --index sp500,ndx100 --months Jul,Aug

# Stricter filters, save full CSV
python screener_cli.py --index sp500,ndx100 --months Jul,Aug --min-win-rate 65 -o output/screener/

# Three consecutive months
python screener_cli.py --index sp500,ndx100 --months Jul,Aug,Sep

# Full universe
python screener_cli.py --index all --top 50

# Compare specific tickers against the universe (shown even if below filters)
python screener_cli.py --index sp500,ndx100 --months Jul,Aug --highlight AMD,DELL

# Show best months for specific tickers (full 12-month breakdown)
python screener_cli.py --index sp500 --lookup AMD,DELL

# All together
python screener_cli.py --index sp500,ndx100 --months Jul,Aug --highlight AMD,DELL --lookup AMD,DELL
```

| Flag | Default | Description |
|------|---------|-------------|
| `--index` / `-i` | `sp500` | `sp500`, `ndx100`, `iwm1000`, `russell3000`, `all` |
| `--months` / `-m` | next 2 months | e.g. `Jul,Aug` or `Jul,Aug,Sep` |
| `--min-win-rate` | `60.0` | Min win rate % per target month |
| `--min-return` | `1.0` | Min mean return % per target month |
| `--min-count` | `5` | Min years of data per month |
| `--top` | `30` | Rows to show in terminal |
| `--highlight` | — | Force-show tickers regardless of filters, show their universe rank |
| `--lookup` | — | Full 12-month breakdown + best windows for specific tickers |
| `--watchlist` / `-w` | — | TradingView watchlist `.txt` — all US tickers become highlight + lookup targets |
| `--output` / `-o` | — | Directory to save full ranked CSV |

### --watchlist

Accepts a TradingView watchlist export (`.txt`). Automatically feeds all US-exchange
tickers into both `--highlight` and `--lookup`, so you see:
- Where each portfolio stock ranks for the target months
- Why it failed the filters (if it did)
- Its full 12-month seasonal breakdown + best windows

```bash
# Check your portfolio for next 2 months
python screener_cli.py --index all --watchlist user_input/tickers/Ioa_port.txt

# Explicit month window
python screener_cli.py --index all --months Jul,Aug --watchlist user_input/tickers/Ioa_port.txt
```

**TradingView export format** (what the file looks like):
```
###SEMIS,NASDAQ:NVDA,NASDAQ:AMD,NYSE:TSM,###MEMORY,NASDAQ:MU,...
```
Section headers (`###NAME`) are ignored. Tickers with US exchanges (NASDAQ, NYSE,
AMEX, CBOE) are parsed; non-US exchanges (GETTEX, TRADEGATE, etc.) are skipped
with a warning.

**Where to save watchlist files:** `user_input/tickers/`
Export from TradingView → Watchlist menu → Export → save `.txt` there.

**Tip:** use `--index all` to maximise coverage — your portfolio likely spans
sp500, ndx100, iwm1000 and russell3000. Tickers not in any downloaded index
show as "not found" with `—` stats.

---

## best_trade_cli.py — Best entry/exit day scanner

For a specific ticker, scans all (entry day, exit day) combinations and finds
the statistically strongest trade windows within a month range.
Run *after* `screener_cli.py` has identified candidates.

```bash
# Single ticker (SPY)
python best_trade_cli.py user_input/jobs/best_trade_spy.csv

# NDX100 batch
python best_trade_cli.py user_input/jobs/best_trade_ndx100.csv --workers 4

# Skip chart, CSV only
python best_trade_cli.py user_input/jobs/best_trade_spy.csv --no-chart

# Custom output directory
python best_trade_cli.py user_input/jobs/best_trade_spy.csv -o output/best_trade/
```

| Flag | Default | Description |
|------|---------|-------------|
| `--output` / `-o` | per-job config | Override output directory |
| `--workers` / `-w` | `1` | Parallel workers |
| `--no-chart` | off | Save CSV only, skip PNG chart |
| `--quiet` / `-q` | off | Suppress progress output |

Input job CSVs live in `user_input/jobs/`. Key columns: `ticker`, `start_year`,
`win_rate_threshold` (default 75%), `profit_factor_threshold` (default 1.5).

**Output per ticker:** `{job_id}_best_trades.csv` + `{job_id}_top20_chart.png`

---

## Typical workflow

```bash
# Once per year — refresh data and pre-compute summaries
python seasonality_cli.py user_input/jobs/sp500_standard_charts.csv --workers 4
python seasonality_cli.py user_input/jobs/ndx100_standard_charts.csv --workers 4
python summary_cli.py

# Start of each month — find best seasonal trades coming up
python screener_cli.py --index sp500,ndx100

# Have a specific ticker in mind?
python screener_cli.py --index sp500,ndx100 --months Jul,Aug --highlight AMD,DELL --lookup AMD,DELL

# Use your TradingView watchlist directly
python screener_cli.py --index all --months Jul,Aug --watchlist user_input/tickers/Ioa_port.txt

# Decided to trade — find best entry/exit day
python best_trade_cli.py user_input/jobs/best_trade_spy.csv
```

---

---

# Reference

---

## Chart types (seasonality_cli.py)

| `chart_type` | Short alias | Description |
|---|---|---|
| `Calendar Day (1-31)` | `calendar_day` | Return by calendar day of month |
| `Trading Day (1-22)` | `trading_day` | Return by trading day of month |
| `Weekly Payroll (W1-5)` | `weekly_payroll` | Payroll week effect |
| `Weekday Effect` | `weekday_effect` | Mon–Fri patterns |
| `Monthly (Jan-Dec)` | `monthly` | Calendar month seasonality |
| `Quarterly Halves` | `quarterly` | Each quarter split into 2 halves |
| `Annual Window` | `annual_window` | Custom date window (e.g. Oct15–Dec31) |
| `Grouping of Days` | `grouping` | Month split into configurable day-range groups |
| `Seasonal Run` | `seasonal_run` | Consecutive reliable periods |
| `Best/Worst Periods` | `best_worst` | Top N best/worst periods |
| `Bernstein Composite` | `composite` | Weekly 0–100 normalized line, green/red + ↑ arrows |

### Phase 1 — input CSV columns

| Column | Default | Description |
|---|---|---|
| `job_id` | — | Output filename prefix |
| `ticker` / `ticker_file` | — | Single ticker or path to ticker list (expands to one job per ticker) |
| `chart_type` | — | See chart types table above |
| `start_year` | all history | First year to include |
| `end_year` | latest | Last year to include |
| `exclude_years` | none | Semicolon-separated years to skip, e.g. `2008;2020` |
| `aggregation` | `Simple Average` | `Simple Average` \| `Median` \| `Weighted Average` |
| `data_type` | `Returns` | `Returns` \| `Prices` \| `Log Returns` |
| `normalization` | `None` | `None` \| `Start=100` \| `Scale 0-100` \| `Z-Score` \| `Winsorize` |
| `detrend_enabled` | `false` | `true` \| `false` |
| `detrend_method` | `Linear` | `Linear` \| `Mean` |
| `alignment` | `None` | `None` \| `Majority Rule` \| `Weekday-Week` |
| `logic_calc` | `average_daily` | `average_daily` \| `open_close_month` \| `open_close_period` |
| `y_axis_metric` | `Average Return` | `Average Return` \| `Win Rate` \| `Cumulative Return` \| `Annualized (CAGR)` \| `Annualized (Bowley 252x)` |
| `show_bands` | `false` | Show min/max range band |
| `show_reliability` | `false` | Highlight consecutive high-win-rate runs |
| `smoothing_period` | `1` | Moving average window (1 = off) |
| `day_groups` | `1-6,7-12,13-18,19-25,26-31` | **Grouping of Days only** — comma-separated ranges |
| `quarter_split_day` | `15` | **Quarterly Halves only** — day-of-month to split each quarter |
| `win_rate_arrow_threshold` | `65.0` | **Bernstein Composite only** — % win rate to draw ↑ arrow |
| `output_path` | `output/` | Output directory |

### Quarterly Halves — default split (quarter_split_day = 15)

| Period | Range |
|---|---|
| Q1 1st | Jan 1 – Feb 15 |
| Q1 2nd | Feb 16 – Mar 31 |
| Q2 1st | Apr 1 – May 15 |
| Q2 2nd | May 16 – Jun 30 |
| Q3 1st | Jul 1 – Aug 15 |
| Q3 2nd | Aug 16 – Sep 30 |
| Q4 1st | Oct 1 – Nov 15 |
| Q4 2nd | Nov 16 – Dec 31 |

### Output file naming

| Suffix in `job_id` | Meaning |
|---|---|
| `_ab` | Average Return + **B**ands (`show_bands=true`) |
| `_ar` | Average Return + **R**eliability (`show_reliability=true`) |
| `_cagr` | Y-axis = Annualized CAGR |
| `_wr` | Y-axis = **W**in **R**ate |

---

## Data sources

### Ticker file format

```
# Format: TICKER[,source]
# source: yf | stooq | local  (blank = auto)
SPY,
QQQ,
^DJI,local
AAPL,yf
```

| Source | Behaviour |
|---|---|
| *(blank)* / `auto` | Check `hist_data/` first → fall back to Yahoo Finance |
| `yf` | Yahoo Finance only |
| `stooq` | Read from `hist_data/` (manually downloaded) |
| `local` | `hist_data/` only — hard error if file not found |

### Long-history local files (hist_data)

For tickers where Yahoo Finance history is insufficient (e.g. DJIA back to 1896),
place a manually downloaded CSV in `user_input/tickers/hist_data/{TICKER}.csv`.

Required columns: `Date, Open, High, Low, Close, Volume` (Date as `YYYY-MM-DD`).

**Example — DJIA from Stooq:**
1. Download from `stooq.com/q/d/?s=^dji`, select Max range, CSV format
2. Save as `user_input/tickers/hist_data/^DJI.csv`
3. Set ticker file entry to `^DJI,local`

### Cache

Yahoo Finance downloads are cached in `data/cache/` for 24 hours.
Delete files there to force a fresh download.

---

## Phase 2 — input CSV columns (best_trade_cli.py)

| Column | Default | Description |
|---|---|---|
| `job_id` | — | Output filename prefix |
| `ticker` / `ticker_file` | — | Single ticker or path to ticker list |
| `start_year` / `end_year` | all / today | Date scope |
| `exclude_years` | none | Semicolon-separated years to skip |
| `entry_months` | all | Months to scan for entry, e.g. `11;12` = Nov+Dec |
| `min_days_in_trade` | `5` | Shortest window (calendar days) |
| `max_days_in_trade` | `45` | Longest window (calendar days) |
| `stop_pct` | `9.0` | Max Adverse Excursion % filter |
| `min_years` | `15` | Minimum years of data required |
| `win_rate_threshold` | `75.0` | Minimum % of profitable years |
| `profit_factor_threshold` | `1.50` | Minimum gross profit ÷ gross loss |
| `max_consec_losses` | `999` | Max consecutive losing years (999 = off) |
| `direction` | `long` | `long` \| `short` |
| `top_n` | `20` | Trades shown in the chart |
| `save_chart` | `true` | Whether to save the PNG chart |
| `output_path` | `output/best_trade/` | Output directory |

**Tuning tips:**
- More results → lower `win_rate_threshold` (e.g. 70) or `profit_factor_threshold` (e.g. 1.2)
- Stricter → raise `win_rate_threshold` (e.g. 80) or lower `stop_pct` (e.g. 5)
- Different season → change `entry_months` (e.g. `"1;2"` for Jan+Feb)
- Longer trades → raise `max_days_in_trade` (e.g. 90)

### Output CSV columns

| Column | Meaning |
|---|---|
| `entry_date` / `exit_date` | MM/DD — buy/sell at close |
| `days_in_trade` | Window length in calendar days |
| `pct_win` | Win rate % across all years |
| `pl_ratio` | Profit factor (gross profit ÷ gross loss). >1.5 good, >3 strong |
| `avg_profit` / `avg_loss` | Average return on winning / losing years |
| `max_win` / `max_loss` | Best / worst single-year return |
| `max_up_swing` | Max Favourable Excursion (best intra-trade close vs entry) |
| `max_stop` | Max Adverse Excursion (worst intra-trade close vs entry) |
| `growth` | Cumulative sum of all annual returns over the full lookback |
| `max_consec_losses` | Longest streak of consecutive losing years |
| `rank_score` | Sort key: `(win_rate × pl_ratio) / (1 + max_stop/100)` |

### Bar chart

- **Bar length** = Win Rate % (longer = more consistent)
- **Colour** = green ≥75%, amber 60–74%, red <60%
- **Label** = `PL:<profit_factor>  +<avg_profit>% / <avg_loss>%  growth:<cumulative>%  yrs:<n_years>`
- **Dashed line** = 75% win rate reference

---

## Directory layout

```
seasonality_lab/
├── seasonality_cli.py            ← Step 0: chart & stats generation
├── summary_cli.py                ← Step 1: best windows per ticker
├── screener_cli.py               ← Step 2: top-performer screener
├── best_trade_cli.py             ← Step 3: best entry/exit day scanner
├── USAGE.md                      ← this file
├── requirements.txt
│
├── user_input/
│   ├── jobs/                     ← job CSVs you run
│   └── tickers/                  ← ticker list files
│       ├── sp500_tickers.csv
│       ├── nasdaq100_tickers.csv
│       ├── russell3000_tickers.csv
│       ├── iwm1000_tickers.csv
│       └── hist_data/            ← long-history CSVs (e.g. ^DJI.csv)
│
├── output/
│   ├── git_download/             ← stats CSVs read by screener + summary
│   │   ├── sp500/
│   │   ├── ndx100/
│   │   ├── iwm1000/
│   │   └── russell3000/
│   ├── summary/                  ← best_windows CSVs (summary_cli.py output)
│   ├── screener/                 ← screener ranked CSVs (optional --output)
│   └── best_trade/               ← best trade CSVs + charts
│
├── src/
│   ├── data/data_loader.py       ← YF + local loading, 24h cache
│   └── core/
│       ├── stamper.py
│       ├── bernstein_config.py
│       ├── bernstein_result.py
│       ├── engine.py
│       ├── batch.py
│       ├── bernstein_chart.py
│       ├── legacy_charts.py
│       └── best_trade.py
│
└── data/cache/                   ← YF download cache (auto-created, 24h TTL)
```
