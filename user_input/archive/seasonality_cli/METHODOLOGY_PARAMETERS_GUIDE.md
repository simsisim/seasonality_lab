# Methodology Parameters Guide

**Complete reference for calculation and processing parameters in CLI CSV**

---

## Overview

Control HOW the seasonality analysis is calculated using these 10 methodology columns:

| Column | Type | Options | Default | Purpose |
|--------|------|---------|---------|---------|
| `aggregation` | string | See below | `Simple Average` | How to combine multiple values |
| `data_type` | string | See below | `Returns` | What data to analyze |
| `use_log_returns` | bool | `true`/`false` | `false` | Use logarithmic returns |
| `normalization` | string | See below | `None` | How to normalize data |
| `detrend_enabled` | bool | `true`/`false` | `false` | Remove trend from data |
| `detrend_method` | string | See below | `Linear` | Detrending algorithm |
| `convergence_enabled` | bool | `true`/`false` | `false` | Enable convergence analysis |
| `smoothing_period` | int | 1-50 | `1` | Smoothing window size |
| `alignment` | string | See below | `None` | Date alignment method |
| `logic_calc` | string | See below | `average_daily` | Calculation logic |

---

## 1. Aggregation Methods

**Column:** `aggregation`

**Controls:** How to combine multiple data points into a single value

### Options

| Value | Description | When to Use | Example |
|-------|-------------|-------------|---------|
| `Simple Average` | Arithmetic mean | Default, most common | Average of all January returns |
| `Weighted Average` | Weight recent data more | Emphasize recent patterns | Weight last 5 years 2×, rest 1× |
| `Median` | Middle value | Robust to outliers | Ignore extreme outlier months |

### Examples

```csv
# Compare different aggregation methods
job_id,ticker,chart_type,aggregation,output_path,notes
spy_avg,SPY,Monthly (Jan-Dec),Simple Average,output/agg/,Standard average
spy_weighted,SPY,Monthly (Jan-Dec),Weighted Average,output/agg/,Recent data weighted more
spy_median,SPY,Monthly (Jan-Dec),Median,output/agg/,Robust to outliers
```

**Use Case:** Compare if recent patterns differ from historical average

---

## 2. Data Type

**Column:** `data_type`

**Controls:** What type of data to analyze

### Options

| Value | Description | Formula | When to Use |
|-------|-------------|---------|-------------|
| `Returns` | Price changes | `(Close[t] - Close[t-1]) / Close[t-1] * 100` | Default, standard analysis |
| `Prices` | Absolute prices | `Close[t]` | Rare, mostly for price level analysis |
| `Log Returns` | Natural log returns | `ln(Close[t] / Close[t-1]) * 100` | Better for compounding, large moves |

### Examples

```csv
# Compare returns vs log returns
job_id,ticker,chart_type,data_type,output_path
spy_returns,SPY,Monthly (Jan-Dec),Returns,output/datatype/
spy_log,SPY,Monthly (Jan-Dec),Log Returns,output/datatype/
```

**Note:** For most cases, use `Returns` (default). Use `Log Returns` for assets with very high volatility (crypto, penny stocks).

---

## 3. Log Returns Toggle

**Column:** `use_log_returns`

**Controls:** Alternative way to enable log returns

### Options

| Value | Description |
|-------|-------------|
| `false` | Use simple returns (default) |
| `true` | Use logarithmic returns |

**Note:** This is an alternative to setting `data_type=Log Returns`. They do the same thing.

### Examples

```csv
# Two ways to enable log returns
job_id,ticker,chart_type,data_type,use_log_returns
spy_method1,SPY,Monthly (Jan-Dec),Log Returns,false
spy_method2,SPY,Monthly (Jan-Dec),Returns,true
```

**Recommendation:** Use `data_type` column for clarity

---

## 4. Normalization

**Column:** `normalization`

**Controls:** How to standardize data for comparison

### Options

| Value | Description | Formula | When to Use |
|-------|-------------|---------|-------------|
| `None` | No normalization | Original values | Default |
| `Z-Score` | Standardize to mean=0, std=1 | `(x - mean) / std` | Compare assets with different volatility |
| `Min-Max` | Scale to 0-1 range | `(x - min) / (max - min)` | Visualize relative magnitude |

### Examples

```csv
# Compare SPY and BTC with different volatilities
job_id,ticker,chart_type,normalization,output_path,notes
spy_raw,SPY,Monthly (Jan-Dec),None,output/norm/,SPY raw returns
btc_raw,BTC-USD,Monthly (Jan-Dec),None,output/norm/,BTC raw returns (much larger)
spy_zscore,SPY,Monthly (Jan-Dec),Z-Score,output/norm/,SPY standardized
btc_zscore,BTC-USD,Monthly (Jan-Dec),Z-Score,output/norm/,BTC standardized (now comparable)
```

**Use Case:** When comparing assets with very different volatilities (stocks vs crypto, large cap vs small cap)

---

## 5. Detrending

**Columns:** `detrend_enabled`, `detrend_method`

**Controls:** Remove long-term trend from data to isolate cycles

### When to Use

✅ **Use detrending when:**
- Asset has strong long-term trend (bull market)
- Want to isolate seasonal patterns independent of trend
- Analyzing trending assets (tech stocks in bull market)

❌ **Don't use detrending when:**
- Already analyzing returns (not prices)
- Trend is part of the pattern you want to see
- Working with mean-reverting assets

### Options for `detrend_method`

| Value | Description | Best For | Speed |
|-------|-------------|----------|-------|
| `Linear` | Straight line fit | Simple upward/downward trends | Fast |
| `HP Filter` | Hodrick-Prescott filter | Smooth trends with noise | Medium |
| `Moving Average` | Rolling average | Quick trend estimation | Fast |

### Examples

```csv
# Compare with and without detrending
job_id,ticker,chart_type,detrend_enabled,detrend_method,output_path,notes
nvda_raw,NVDA,Monthly (Jan-Dec),false,,output/detrend/,NVDA raw (strong uptrend visible)
nvda_detrended,NVDA,Monthly (Jan-Dec),true,Linear,output/detrend/,NVDA detrended (cycle isolated)
```

**Important:** Usually NOT needed for seasonality since we're already using returns (which remove trend by definition)

---

## 6. Convergence

**Column:** `convergence_enabled`

**Controls:** Enable convergence analysis (advanced)

### Options

| Value | Description |
|-------|-------------|
| `false` | Standard analysis (default) |
| `true` | Enable convergence detection |

**Note:** Advanced feature for detecting if patterns are converging over time

---

## 7. Smoothing

**Column:** `smoothing_period`

**Controls:** Apply moving average smoothing to reduce noise

### Options

| Value | Description | Effect |
|-------|-------------|--------|
| `1` | No smoothing (default) | Raw data |
| `3` | 3-period moving average | Light smoothing |
| `5` | 5-period moving average | Medium smoothing |
| `10` | 10-period moving average | Heavy smoothing |

### Examples

```csv
# Compare different smoothing levels
job_id,ticker,chart_type,smoothing_period,output_path,notes
spy_raw,SPY,Calendar Day (1-31),1,output/smooth/,No smoothing - see all noise
spy_smooth3,SPY,Calendar Day (1-31),3,output/smooth/,3-day smoothing - cleaner
spy_smooth5,SPY,Calendar Day (1-31),5,output/smooth/,5-day smoothing - smoothest
```

**Use Case:** Calendar Day and Trading Day charts can be noisy - smoothing helps identify patterns

**Recommendation:**
- Calendar/Trading Day: Try `smoothing_period=3` or `5`
- Monthly/Quarterly: Keep at `1` (already aggregated)

---

## 8. Alignment

**Column:** `alignment`

**Controls:** How to align dates for seasonality aggregation

### Options

| Value | Description | When to Use |
|-------|-------------|-------------|
| `None` | No alignment (default) | Most cases |
| `Majority Rule` | Align by most common weekday | Calendar Day analysis with weekend issues |
| `Weekday-Week` | Align by week and weekday | Weekday Effect analysis |

### Examples

```csv
# Calendar day alignment
job_id,ticker,chart_type,alignment,output_path,notes
spy_none,SPY,Calendar Day (1-31),None,output/align/,No alignment
spy_majority,SPY,Calendar Day (1-31),Majority Rule,output/align/,Align to majority weekday
```

**Use Case:** When day-of-month falls on different weekdays (e.g., 15th is sometimes Monday, sometimes Friday)

---

## 9. Calculation Logic

**Column:** `logic_calc`

**Controls:** What calculation method to use for the chart

### Options

| Value | Description | Best For |
|-------|-------------|----------|
| `average_daily` | Average daily returns | Calendar Day, Trading Day, Weekday |
| `open_close_month` | Month open to close | Monthly charts |
| `open_close_period` | Period open to close | Quarterly, Annual Window |

### Examples

```csv
# Different calculation methods
job_id,ticker,chart_type,logic_calc,notes
spy_monthly,SPY,Monthly (Jan-Dec),open_close_month,Month's open to close return
spy_calendar,SPY,Calendar Day (1-31),average_daily,Average return for each calendar day
spy_quarterly,SPY,Quarterly Halves,open_close_period,Quarter's open to close return
```

**Recommendation:** Use defaults - the system auto-selects the right method for each chart type

---

## Complete Methodology Example

**Comprehensive CSV with all methodology parameters:**

```csv
job_id,ticker,data_source,interval,start_year,end_year,chart_type,aggregation,data_type,use_log_returns,normalization,detrend_enabled,detrend_method,convergence_enabled,smoothing_period,alignment,logic_calc,y_axis_metric,output_format,output_path,notes
spy_standard,SPY,yahoo,1d,2000,2026,Monthly (Jan-Dec),Simple Average,Returns,false,None,false,,false,1,None,open_close_month,Average Return,png,output/complete/,Standard methodology
spy_robust,SPY,yahoo,1d,2000,2026,Monthly (Jan-Dec),Median,Returns,false,None,false,,false,1,None,open_close_month,Average Return,png,output/complete/,Robust to outliers
spy_normalized,SPY,yahoo,1d,2000,2026,Monthly (Jan-Dec),Simple Average,Returns,false,Z-Score,false,,false,1,None,open_close_month,Average Return,png,output/complete/,Normalized for comparison
spy_smoothed,SPY,yahoo,1d,2000,2026,Calendar Day (1-31),Simple Average,Returns,false,None,false,,false,5,Majority Rule,average_daily,Average Return,png,output/complete/,5-day smoothing with alignment
nvda_detrended,NVDA,yahoo,1d,2015,2026,Monthly (Jan-Dec),Simple Average,Returns,false,None,true,Linear,false,1,None,open_close_month,Average Return,png,output/complete/,Detrended for strong trend
btc_log,BTC-USD,yahoo,1d,2017,2026,Monthly (Jan-Dec),Simple Average,Log Returns,true,None,false,,false,1,None,open_close_month,Average Return,png,output/complete/,Log returns for high volatility
```

---

## Common Methodology Combinations

### Combination 1: Standard Analysis (Default)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Simple Average,Returns,None,false,1
```
**Use for:** Most analyses, default behavior

---

### Combination 2: Robust Analysis (Outlier-resistant)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Median,Returns,None,false,1
```
**Use for:** When you have extreme outlier events (flash crashes, black swans)

---

### Combination 3: High Volatility Assets (Crypto, Penny Stocks)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Simple Average,Log Returns,Z-Score,false,1
```
**Use for:** Bitcoin, altcoins, highly volatile small caps

---

### Combination 4: Smooth Calendar Day Patterns
```csv
aggregation,data_type,normalization,smoothing_period,alignment
Simple Average,Returns,None,5,Majority Rule
```
**Use for:** Calendar Day (1-31) and Trading Day (1-22) charts

---

### Combination 5: Trending Asset Analysis
```csv
aggregation,data_type,detrend_enabled,detrend_method,smoothing_period
Simple Average,Returns,true,Linear,1
```
**Use for:** Assets in strong secular bull/bear markets (tech stocks 2010-2020)

---

### Combination 6: Cross-Asset Comparison
```csv
aggregation,data_type,normalization,detrend_enabled
Simple Average,Returns,Z-Score,false
```
**Use for:** Comparing assets with vastly different characteristics (SPY vs BTC vs bonds)

---

## Quick Reference Table

| Goal | Parameters to Set |
|------|-------------------|
| **Standard analysis** | All defaults (don't specify anything) |
| **Reduce noise** | `smoothing_period=3` or `5` |
| **Handle outliers** | `aggregation=Median` |
| **Compare different volatilities** | `normalization=Z-Score` |
| **Isolate cycle from trend** | `detrend_enabled=true, detrend_method=Linear` |
| **High volatility asset** | `data_type=Log Returns` or `use_log_returns=true` |
| **Calendar day alignment** | `alignment=Majority Rule` |

---

## Methodology Testing Template

**Test different methodologies on the same ticker:**

```csv
job_id,ticker,chart_type,aggregation,data_type,normalization,detrend_enabled,smoothing_period,output_path,notes
test_1_baseline,SPY,Monthly (Jan-Dec),Simple Average,Returns,None,false,1,output/test/,Baseline - all defaults
test_2_median,SPY,Monthly (Jan-Dec),Median,Returns,None,false,1,output/test/,Test median aggregation
test_3_normalized,SPY,Monthly (Jan-Dec),Simple Average,Returns,Z-Score,false,1,output/test/,Test normalization
test_4_log,SPY,Monthly (Jan-Dec),Simple Average,Log Returns,None,false,1,output/test/,Test log returns
test_5_smoothed,SPY,Monthly (Jan-Dec),Simple Average,Returns,None,false,3,output/test/,Test smoothing
test_6_detrended,SPY,Monthly (Jan-Dec),Simple Average,Returns,None,true,1,output/test/,Test detrending
```

---

## Recommendations by Chart Type

### Monthly (Jan-Dec)
```csv
aggregation,smoothing_period,logic_calc
Simple Average,1,open_close_month
```

### Calendar Day (1-31)
```csv
aggregation,smoothing_period,alignment,logic_calc
Simple Average,5,Majority Rule,average_daily
```

### Trading Day (1-22)
```csv
aggregation,smoothing_period,logic_calc
Simple Average,3,average_daily
```

### Quarterly Halves
```csv
aggregation,smoothing_period,logic_calc
Simple Average,1,open_close_period
```

### Weekday Effect
```csv
aggregation,alignment,logic_calc
Simple Average,Weekday-Week,average_daily
```

---

## Examples by Asset Class

### Large Cap Stocks (SPY, AAPL, MSFT)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Simple Average,Returns,None,false,1
```

### High Growth Tech (NVDA, TSLA)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Simple Average,Returns,None,true,1
```

### Cryptocurrency (BTC, ETH)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Median,Log Returns,Z-Score,false,3
```

### Commodities (GLD, SLV, USO)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Simple Average,Returns,None,false,1
```

### Bonds (TLT, AGG)
```csv
aggregation,data_type,normalization,detrend_enabled,smoothing_period
Simple Average,Returns,None,false,1
```

---

## Template File Created

**File:** `templates/seasonality_cli/cli_batch_methodology.csv`

Contains 7 example jobs showing different methodology combinations:
1. Raw returns (baseline)
2. Log returns
3. Z-score normalization
4. Linear detrending
5. 5-period smoothing
6. Median aggregation
7. Weighted average

**Run this to compare methodologies side-by-side!**

---

**Summary:** You have full control over calculation methodology. For most cases, the defaults work great. Use these parameters when you need to:
- Handle outliers (median)
- Compare different assets (normalization)
- Reduce noise (smoothing)
- Isolate cycles (detrending)
- Handle high volatility (log returns)
