## ✅ CSV Format Created!

I've designed a comprehensive CSV format that controls **everything** - from data download to chart generation. Here's the summary:

### 📋 CSV Structure (55 total columns)

**Organized in 9 categories:**

1. **Job Identification** (2 columns): `job_id`, `notes`
2. **Data Loading** (6 columns): `ticker`, `data_source`, `interval`, `download_start_date`, `download_end_date`, `data_cache`
3. **Analysis Period** (4 columns): `start_year`, `end_year`, `end_month`, `lookback_years`
4. **Chart Configuration** (3 columns): `chart_type`, `y_axis_metric`, `output_type`
5. **Data Filtering** (7 columns): `exclude_years`, `filter_regime`, `filter_decennial`, etc.
6. **Data Processing** (10 columns): `aggregation`, `normalization`, `detrend_enabled`, etc.
7. **Visualization** (13 columns): `show_winrate`, `show_bands`, `show_sample_size`, etc.
8. **Output Configuration** (3 columns): `output_format`, `output_path`, `save_data`
9. **Execution Control** (2 columns): `enabled`, `priority`

---

### 🎯 Key Innovation: Data Download Control

**NEW columns for autonomous data loading:**

| Column | Example | Description |
|--------|---------|-------------|
| `ticker` | `SPY` | Symbol to download from Yahoo Finance |
| `data_source` | `yahoo` | Data source (`yahoo`, `yfi`, `auto`) |
| `interval` | `1d` | Frequency: `1d` (daily), `1wk` (weekly), `1mo` (monthly) |
| `download_start_date` | `max` or `2000-01-01` | Start of data download (use `max` for all available) |
| `download_end_date` | `latest` or `2026-12-31` | End of data download (use `latest` for most recent) |

**Example:**
```csv
ticker,data_source,interval,download_start_date,download_end_date
SPY,yahoo,1d,max,latest
NVDA,yahoo,1d,2020-01-01,2026-12-31
^GSPC,yahoo,1wk,2000-01-01,latest
```

---

### 📁 Template Files Created

#### 1. **MINIMAL** Template (7 columns) - Start here!

**File:** `cli_batch_minimal.csv`

```csv
job_id,ticker,data_source,interval,chart_type,output_path,notes
spy_monthly,SPY,yahoo,1d,Monthly (Jan-Dec),output/cli_minimal/,S&P 500 monthly
qqq_calendar,QQQ,yahoo,1d,Calendar Day (1-31),output/cli_minimal/,Nasdaq calendar
iwm_trading,IWM,yahoo,1d,Trading Day (1-22),output/cli_minimal/,Russell trading
```

**Use when:** Quick start, testing, simple analyses

---

#### 2. **STANDARD** Template (12 columns) - Most common

**File:** `cli_batch_standard.csv`

Adds: `download_start_date`, `start_year`, `end_year`, `y_axis_metric`, `output_format`

```csv
job_id,ticker,data_source,interval,download_start_date,start_year,end_year,chart_type,y_axis_metric,output_format,output_path,notes
spy_monthly_avg,SPY,yahoo,1d,max,2000,2026,Monthly (Jan-Dec),Average Return,png,output/,SPY monthly avg
spy_monthly_wr,SPY,yahoo,1d,max,2000,2026,Monthly (Jan-Dec),Win Rate,png,output/,SPY monthly win rate
spy_monthly_cagr,SPY,yahoo,1d,max,2000,2026,Monthly (Jan-Dec),Annualized (CAGR),png,output/,SPY monthly CAGR
```

**Use when:** Need specific time periods, different metrics

---

#### 3. **ADVANCED** Template (14 columns) - With filters

**File:** `cli_batch_advanced.csv`

Adds: `exclude_years`, `filter_regime`, `aggregation`

```csv
job_id,ticker,data_source,interval,start_year,end_year,chart_type,exclude_years,filter_regime,...
spy_bull,SPY,yahoo,1d,2000,2026,Monthly (Jan-Dec),,Bull Markets,...
spy_no_crisis,SPY,yahoo,1d,2000,2026,Monthly (Jan-Dec),2008;2009;2020,,...
```

**Use when:** Conditional analysis (bull/bear, exclude years, etc.)

---

### 🎨 Chart Types (12 options)

```csv
chart_type
Calendar Day (1-31)
Trading Day (1-22)
Weekly Payroll (W1-5)
Weekday Effect
Monthly (Jan-Dec)
Quarterly Halves
Annual Window (Oct15-Dec31)
Grouping of Days
JayNewary Barometer
Holiday Barometer
Seasonal Run
Best/Worst Periods
```

---

### 📊 Y-Axis Metrics (5 options)

```csv
y_axis_metric
Average Return
Win Rate
Cumulative Return
Annualized (CAGR)
Annualized (Compound 252×)
Annualized (Bowley)
```

---

### 💡 Example Use Cases

#### Example 1: Multi-Ticker Comparison
```csv
job_id,ticker,data_source,interval,chart_type,output_path
spy_monthly,SPY,yahoo,1d,Monthly (Jan-Dec),output/comparison/
qqq_monthly,QQQ,yahoo,1d,Monthly (Jan-Dec),output/comparison/
iwm_monthly,IWM,yahoo,1d,Monthly (Jan-Dec),output/comparison/
```

#### Example 2: Same Ticker, Different Metrics
```csv
job_id,ticker,chart_type,y_axis_metric,output_path
spy_avg,SPY,Monthly (Jan-Dec),Average Return,output/metrics/
spy_wr,SPY,Monthly (Jan-Dec),Win Rate,output/metrics/
spy_cagr,SPY,Monthly (Jan-Dec),Annualized (CAGR),output/metrics/
```

#### Example 3: Historical Periods
```csv
job_id,ticker,start_year,end_year,chart_type,output_path,notes
spy_90s,SPY,1990,1999,Monthly (Jan-Dec),output/decades/,1990s
spy_00s,SPY,2000,2009,Monthly (Jan-Dec),output/decades/,2000s
spy_10s,SPY,2010,2019,Monthly (Jan-Dec),output/decades/,2010s
spy_20s,SPY,2020,2026,Monthly (Jan-Dec),output/decades/,2020s
```

#### Example 4: All Chart Types for One Ticker
```csv
job_id,ticker,chart_type,output_path
spy_calendar,SPY,Calendar Day (1-31),output/all_charts/
spy_trading,SPY,Trading Day (1-22),output/all_charts/
spy_monthly,SPY,Monthly (Jan-Dec),output/all_charts/
spy_quarterly,SPY,Quarterly Halves,output/all_charts/
...
```

#### Example 5: Bull vs Bear Markets
```csv
job_id,ticker,chart_type,filter_regime,output_path
spy_bull,SPY,Monthly (Jan-Dec),Bull Markets,output/regime/
spy_bear,SPY,Monthly (Jan-Dec),Bear Markets (All),output/regime/
spy_all,SPY,Monthly (Jan-Dec),,output/regime/
```

---

### ⚙️ Data Download Options

**`data_source` options:**
- `yahoo` - Yahoo Finance (recommended)
- `yfi` - Yahoo Finance (alias)
- `auto` - Auto-detect (default)
- `csv` - Load from local CSV file

**`interval` options:**
- `1d` - Daily data (default)
- `1wk` - Weekly data
- `1mo` - Monthly data

**`download_start_date` options:**
- `max` - All available history (recommended)
- `2000-01-01` - Specific date (YYYY-MM-DD format)

**`download_end_date` options:**
- `latest` - Most recent data (recommended)
- `2026-12-31` - Specific date (YYYY-MM-DD format)

---

### 🔍 Filtering Options

**Market Regime:**
```csv
filter_regime
Bull Markets
Bear Markets (All)
Bear (Secular)
Bear (Cyclical)
```

**Exclude Years:**
```csv
exclude_years
2008;2009;2020
```
(Semicolon-separated list)

**Decennial Filter:**
```csv
filter_decennial
0,5
```
(Comma-separated: years ending in 0 or 5)

**Presidential Filters:**
```csv
filter_pres_party,filter_pres_cycle_year,filter_pres_midterm
Democrat,3,Yes
Republican,1,No
```

---

### 📂 Output Options

**`output_format` options:**
- `png` - PNG image (default, fastest)
- `html` - Interactive HTML (larger files)
- `both` - Both PNG and HTML
- `csv_only` - Just data tables, no charts

**`output_path` examples:**
```csv
output_path
output/
output/results/
output/2026-02-06/
/absolute/path/to/results/
```

---

### ✅ Required vs Optional Columns

**REQUIRED (Must have):**
- `job_id` - Unique identifier
- `ticker` - Symbol to analyze
- `chart_type` - Which chart to generate

**HIGHLY RECOMMENDED:**
- `data_source` - Where to get data (defaults to `auto`)
- `output_path` - Where to save (defaults to `output/`)
- `notes` - What this job does

**OPTIONAL (Defaults provided):**
- Everything else! Just add columns as needed

---

### 🚀 Quick Start

**1. Copy MINIMAL template:**
```bash
cp templates/seasonality_cli/cli_batch_minimal.csv my_analysis.csv
```

**2. Edit with your tickers:**
```csv
job_id,ticker,data_source,interval,chart_type,output_path,notes
my_spy,SPY,yahoo,1d,Monthly (Jan-Dec),output/mine/,My SPY analysis
my_aapl,AAPL,yahoo,1d,Monthly (Jan-Dec),output/mine/,My AAPL analysis
```

**3. Run CLI (future):**
```bash
python batch_cli.py my_analysis.csv
```

---

### 📏 Default Values

If you omit a column, these defaults apply:

| Column | Default | Meaning |
|--------|---------|---------|
| `data_source` | `auto` | Auto-detect |
| `interval` | `1d` | Daily |
| `download_start_date` | `max` | All history |
| `download_end_date` | `latest` | Most recent |
| `start_year` | (all) | Use all data |
| `end_year` | (all) | Use all data |
| `y_axis_metric` | `Average Return` | Simple avg |
| `output_format` | `png` | PNG image |
| `output_path` | `output/` | Default folder |

---

### 🎯 Template Progression

**Start simple, add complexity as needed:**

```
MINIMAL (7 columns)
    ↓ Add time periods
STANDARD (12 columns)
    ↓ Add filters
ADVANCED (14 columns)
    ↓ Add processing options
COMPREHENSIVE (55 columns)
```

---

## 📖 Full Documentation

See `CLI_CSV_FORMAT_DESIGN.md` for:
- Complete column reference (all 55 columns)
- Detailed examples
- Validation rules
- Best practices

---

**Files Created:**
- ✅ `cli_batch_minimal.csv` (3 example jobs, 7 columns)
- ✅ `cli_batch_standard.csv` (5 example jobs, 12 columns)
- ✅ `cli_batch_advanced.csv` (5 example jobs, 14 columns)
- ✅ `CLI_CSV_FORMAT_DESIGN.md` (Complete specification)
- ✅ This README

**Status:** Ready for CLI implementation!
