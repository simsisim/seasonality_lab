# Seasonality Batch Mode - CSV Templates Guide

## 📁 Template Files Overview

This directory contains CSV template files for the Seasonality Batch Mode feature. Choose the template that best fits your use case.

---

## 🎯 Quick Start Templates

### 1. **seasonality_batch_template_MINIMAL.csv**
**Best for:** First-time users, simple batch jobs

**What it includes:**
- Only **6 required columns**: job_id, ticker, chart_type, output_format, output_path, notes
- All other settings use defaults
- 3 example rows ready to run

**Use when:**
- You want to quickly generate charts with default settings
- You're new to batch mode and want to start simple
- You trust the default parameters (they're sensible!)

**Example use cases:**
- "Generate monthly charts for SPY, QQQ, and IWM with defaults"
- "Quick calendar day analysis for multiple tickers"

---

### 2. **seasonality_batch_examples_QUICKSTART.csv**
**Best for:** Common real-world scenarios, learning by example

**What it includes:**
- **13 essential columns** (job_id, ticker, chart_type, date range, basic processing, output)
- 10 pre-configured example jobs covering popular use cases
- Mix of equities, crypto, bonds, and commodities

**Use when:**
- You want slightly more control than minimal template
- You need date range filtering or specific metrics
- You're analyzing multiple asset classes

**Example jobs included:**
- S&P 500 monthly (all-time history)
- Nasdaq 100 monthly (recent 15 years)
- Bitcoin monthly (since 2015)
- Calendar day patterns
- Trading day patterns
- Quarterly halves
- Weekday effects

---

### 3. **seasonality_batch_examples_ALL_CHART_TYPES.csv**
**Best for:** Understanding all available chart types

**What it includes:**
- **All 12 chart types** demonstrated with SPY
- Chart-specific parameters shown in JSON format
- Different output formats (PNG, HTML, CSV, both)

**Use when:**
- You want to see examples of every chart type
- You're exploring which chart types to use
- You need reference for chart_specific_params JSON structure

**Chart types covered:**
1. Calendar Day (1-31)
2. Trading Day (1-22)
3. Weekly Payroll (W1-5)
4. Weekday Effect
5. Monthly (Jan-Dec)
6. Quarterly Halves
7. Annual Window
8. Grouping of Days
9. JayNewary Barometer
10. Holiday Barometer
11. Seasonal Run
12. Best/Worst Periods

---

### 4. **seasonality_batch_examples_COMPREHENSIVE.csv**
**Best for:** Power users, advanced filtering and processing

**What it includes:**
- **All 43 columns** fully specified
- Advanced filtering examples (bull/bear markets, presidential cycles, decennial)
- Data processing options (detrending, normalization, log returns)
- Multiple y-axis metrics (CAGR, Compound 252×, Bowley, Win Rate, Cumulative)
- Visualization options (sample size, confidence bands, reliability tiers)

**Use when:**
- You need precise control over every parameter
- You're doing research comparing different methodologies
- You want to see what's possible with the system

**Advanced examples included:**
- Bull markets only analysis
- Bear markets only analysis
- Democrat vs Republican presidency comparison
- Pre-election year (year 3) analysis
- Decennial cycle (years ending in 0, 5)
- Log returns vs regular returns
- Linear detrending
- Different annualization methods
- Lookback mode (most recent N years)

---

### 5. **seasonality_batch_examples_MULTI_TICKER.csv**
**Best for:** Comparative analysis across asset classes

**What it includes:**
- **21 tickers** organized by category
- Consistent settings for easy comparison
- Output paths organized by asset class

**Categories:**
- **Indices:** SPY, QQQ, DIA, IWM
- **Sectors:** XLK, XLF, XLV, XLE, XLP, XLY
- **Commodities:** GLD, SLV, USO, DBA
- **Bonds:** TLT, IEF, SHY, LQD, HYG
- **Crypto:** BTC-USD, ETH-USD

**Use when:**
- You want to compare seasonality across sectors
- You're building a sector rotation strategy
- You need to see which asset classes have strongest seasonal patterns

---

### 6. **seasonality_batch_examples_SPECIALIZED.csv**
**Best for:** Specific trading strategies and deep-dives

**What it includes:**
- **29 specialized jobs** for advanced strategies
- Holiday-specific analysis (Thanksgiving, Christmas, July 4th)
- Seasonal run detection with varying parameters
- Best/Worst period rankings
- Custom day groupings (turn-of-month, options expiry)
- Famous seasonal effects (Halloween, Santa Rally, Sell in May)
- Crisis period exclusions
- Market regime filtering

**Use when:**
- You're researching specific seasonal patterns (holidays, turn-of-month)
- You want to detect seasonal runs with custom thresholds
- You're testing well-known seasonal effects
- You need to exclude crisis periods from analysis

**Specialized analyses included:**
- **Holiday Effects:** Individual holidays (±3 days)
- **Seasonal Runs:** Daily, weekly, monthly with varying strictness
- **Rankings:** Top/bottom N periods of year/quarter
- **Custom Groups:** Turn-of-month, options expiry week
- **Famous Effects:** Halloween, Santa Rally, Sell in May
- **Crisis Comparison:** With/without 2008, 2020
- **Regime Filtering:** Bull/bear/secular/cyclical markets

---

### 7. **seasonality_batch_template_BLANK.csv**
**Best for:** Creating custom configurations from scratch

**What it includes:**
- Header row only with all 43 column names
- No example data
- Clean slate for your own jobs

**Use when:**
- You want to build your own CSV from scratch
- You're importing/generating configs programmatically
- You need column names reference

---

## 📊 Column Reference Quick Guide

### Required Columns (Minimal Template)
| Column | Type | Example | Notes |
|--------|------|---------|-------|
| `job_id` | string | "SPY_monthly_2020" | Unique identifier for this job |
| `ticker` | string | "SPY" | Symbol to analyze |
| `chart_type` | enum | "Monthly (Jan-Dec)" | One of 12 chart types |
| `output_format` | enum | "png" | png / html / both / csv_only |
| `output_path` | string | "output/batch/" | Where to save results |
| `notes` | string | "S&P 500 analysis" | Human-readable description |

### Essential Columns (QuickStart Template)
Add these to minimal for more control:
- `start_year` / `end_year` - Date range filtering
- `aggregation` - Simple Average / Median / Win-Rate Weighted
- `data_type` - Returns / Log Returns / Prices
- `alignment` - None / Majority Rule / Weekday-Week
- `output_type` - Bar / Line / Heatmap / Grouped Bar / Table+Chart
- `logic_calc` - average_daily / open_close_month / forward_return_21d
- `y_axis_metric` - Average Return / Win Rate / Cumulative / Annualized (CAGR) / Annualized (Compound 252×, Bowley)

### Advanced Columns (Comprehensive Template)
Add these for maximum control:
- **Filtering:** exclude_years, filter_regime, filter_decennial, filter_pres_*
- **Processing:** detrend_enabled/method, normalization, convergence_enabled, smoothing_period
- **Visualization:** show_winrate, show_sample_size, show_confidence_tiers, show_sample_warnings
- **Chart-Specific:** chart_specific_params (JSON for complex settings)

---

## 🎨 Output Format Options

| Format | Use Case | File Extensions | Notes |
|--------|----------|----------------|-------|
| `png` | Static images for reports | .png | Default, always works |
| `html` | Interactive charts | .html | Hover tooltips, zoom/pan |
| `both` | Maximum flexibility | .png + .html | Best for important analyses |
| `csv_only` | Data export only | .csv (tables) | For Best/Worst, Barometers |

---

## 🚀 How to Use These Templates

### Option 1: Use As-Is
1. Choose appropriate template
2. Copy to your project's `batch_configs/` folder
3. Run batch processor
4. Find results in specified output paths

### Option 2: Customize
1. Open template in Excel/Google Sheets/text editor
2. Modify tickers, date ranges, parameters as needed
3. Add/remove rows for your specific jobs
4. Save as CSV
5. Run batch processor

### Option 3: Programmatic Generation
```python
import pandas as pd

# Read template as starting point
template_df = pd.read_csv('seasonality_batch_template_MINIMAL.csv')

# Generate rows programmatically
jobs = []
for ticker in ['SPY', 'QQQ', 'IWM']:
    for chart_type in ['Monthly (Jan-Dec)', 'Calendar Day (1-31)']:
        jobs.append({
            'job_id': f"{ticker}_{chart_type.replace(' ', '_')}",
            'ticker': ticker,
            'chart_type': chart_type,
            'output_format': 'png',
            'output_path': f'output/batch_{ticker}/',
            'notes': f'{ticker} {chart_type} analysis'
        })

# Save as new CSV
pd.DataFrame(jobs).to_csv('my_custom_batch.csv', index=False)
```

---

## 📖 Column Documentation

For complete documentation of all 43 columns, see:
- **Full Implementation Plan:** `CSV_BATCH_MODE_IMPLEMENTATION_PLAN.md` (Section 2.2)
- **Column Reference Table:** Section 13.A in implementation plan
- **Default Values:** Section 13.C in implementation plan

---

## ⚠️ Common Mistakes to Avoid

1. **Missing Required Columns:** job_id, ticker, chart_type are REQUIRED
2. **Invalid Enum Values:** Check spelling/capitalization (e.g., "Bull Markets" not "bull markets")
3. **Date Format:** Use integers for years (2020, not "2020")
4. **Boolean Values:** Use "true"/"false" or "1"/"0", not "True"/"False"
5. **JSON Syntax:** chart_specific_params must be valid JSON (use double quotes)
6. **Output Paths:** Use forward slashes even on Windows ("output/batch/" not "output\batch\")
7. **Semicolon Separators:** For lists use semicolons (exclude_years: "2008;2020", not "2008,2020")

---

## 🔧 Validation Tips

Before running a large batch:
1. **Test with 1-2 rows first** - Catch config errors early
2. **Check column names** - Copy from template to avoid typos
3. **Validate JSON** - Use jsonlint.com for chart_specific_params
4. **Use consistent formatting** - Don't mix "true" and "1" for booleans
5. **Preview in spreadsheet** - Excel/Google Sheets can catch structural issues

---

## 💡 Tips for Best Results

### Performance
- Put quick jobs first (crash-detection pattern)
- Group by ticker (data caching works better)
- Use CSV output only for large ranking tables

### Organization
- Use descriptive job_ids ("SPY_monthly_bull_2000-2020")
- Organize output paths by category ("output/sectors/", "output/indices/")
- Add detailed notes (future you will thank you)

### Reproducibility
- Include start_year/end_year explicitly (don't rely on "latest")
- Document exclude_years reasoning in notes
- Save copy of config CSV with results

---

## 📞 Need Help?

- **Implementation Plan:** See full plan for architecture details
- **Column Reference:** Section 2.2 of implementation plan
- **Examples:** Study the comprehensive/specialized templates
- **Validation:** Run parser with validate_only=True first

---

## 🎯 Recommended Workflow

### For Beginners:
1. Start with **MINIMAL** template
2. Run it, see what defaults produce
3. Graduate to **QUICKSTART** template
4. Add date ranges and specific metrics
5. Study **ALL_CHART_TYPES** to learn options

### For Advanced Users:
1. Start with **QUICKSTART** or **COMPREHENSIVE**
2. Copy relevant examples from **SPECIALIZED**
3. Customize for your specific research questions
4. Build reusable config libraries for common analyses

### For Researchers:
1. Use **COMPREHENSIVE** template as foundation
2. Create systematic variations (change one parameter at a time)
3. Use **MULTI_TICKER** approach for comparative studies
4. Document methodology in notes column

---

**Last Updated:** 2026-02-06
**Compatible With:** Seasonality Engine v1.0 (planned)
