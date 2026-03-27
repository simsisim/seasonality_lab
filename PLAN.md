# Seasonality Bernstein — Implementation Plan

Focused seasonality program using Jack Bernstein's methodology.
No dashboard, no presidential/decennial cycles. Pure CSV-driven CLI.

---

## Usage

```bash
# Generate Bernstein composite weekly charts
python bernstein_cli.py templates/bernstein_batch_minimal.csv

# Run best trade scanner for single ticker
python bernstein_cli.py templates/best_trade_batch.csv

# Multi-ticker screening with parallel workers
python bernstein_cli.py templates/best_trade_nasdaq100.csv --workers 4
```

---

## Project Structure

```
seasonality_Bernstein/
├── PLAN.md                           # This file
├── bernstein_cli.py                  # Entry point (argparse + batch runner)
├── requirements.txt
├── src/
│   ├── data/
│   │   └── data_loader.py            # COPIED verbatim from cycles-dashboard
│   └── core/
│       ├── stamper.py                # TRIMMED from cycle_stamper.py
│       ├── bernstein_config.py       # NEW — slim 12-field config dataclass
│       ├── bernstein_result.py       # NEW — result container (matplotlib only)
│       ├── bernstein_chart.py        # NEW — Bernstein composite weekly chart
│       ├── best_trade.py             # NEW — exhaustive DOY window scanner
│       └── batch.py                  # NEW — CSV batch processor
├── templates/
│   ├── bernstein_batch_minimal.csv   # Composite chart batch template
│   └── best_trade_batch.csv          # Best trade scan template
├── output/                           # Created at runtime
└── data/cache/                       # yfinance cache, auto-created
```

---

## Section 1 — What to MAINTAIN from cycles-dashboard

### Copied verbatim
| Source | Destination | Notes |
|---|---|---|
| `src/data/data_loader.py` | `src/data/data_loader.py` | yfinance + caching, unchanged |

### Derived / trimmed
| Source | Destination | Removed |
|---|---|---|
| `src/historical/cycle_stamper.py` | `src/core/stamper.py` | Presidential, decennial, forward returns |

### Left out entirely
- `seasonality_charts.py` (3,751 lines Plotly) — replaced by matplotlib
- `seasonality_engine.py`, `seasonality_config.py`, `seasonality_processor.py`, `seasonality_analyzer.py`
- All `calendars/` files (presidential, bear markets, barometers)
- `cycle_calculator.py`, `walk_forward.py`, `pattern_analyzer.py`
- All Streamlit UI code

---

## Section 2 — Bernstein Composite Weekly Chart

### Chart description (from charts_template_jack_bernstein.png)
- Title: "WEEKLY SEASONAL STOCK COMPOSITE {TICKER} {start_year} - {end_year}"
- Main panel: normalized price 0-100 — green segment = up week, red = down week
- Bottom row 1: green ↑ arrows on weeks where win_rate >= threshold (default 65%)
- Bottom row 2: 2-digit year labels showing yearly close reference
- Monthly vertical separator lines + month name x-axis labels
- Fine dotted grid, Y-axis 0-100 in steps of 10
- figsize=(16, 7), DPI=150

### Data pipeline
```
Daily OHLCV (yfinance)
  → Resample to weekly (Friday close)
  → Per year: norm = 100 × (close − year_low) / (year_high − year_low)
  → Build pivot: rows=year, cols=ISO week 1-52
  → Column-wise mean → composite[52]
  → Per-week win_rate: % years where week_n > week_n-1
  → Color: green if composite[n] > composite[n-1], else red
  → Draw with matplotlib
  → Save as PNG
```

### Key functions in `src/core/bernstein_chart.py`
- `normalize_bernstein(df)` — per-year Scale 0-100 on close prices, skip incomplete years
- `build_composite(pivot_df)` — mean + win_rate per ISO week
- `draw_bernstein_composite(composite, win_rates, ...)` — full matplotlib render
- `generate_bernstein_chart(df, config)` — main entry point, returns Figure

---

## Section 3 — Best Trade Scanner (Bernstein Screener)

### Algorithm in `src/core/best_trade.py`
Exhaustive scan of all (entry_doy, exit_doy) pairs (DOY 1-365):

For each window:
1. For each year: find entry_price at entry_doy (±3 days), exit_price at exit_doy
2. Compute: win_rate, avg_return, profit_factor, max_drawdown, max_consec_losses
3. Filter: win_rate ≥ 70%, n_years ≥ 15, profit_factor ≥ 1.5
4. Rank: win_rate × profit_factor / (1 + max_drawdown)

### Output per ticker
- `{job_id}_best_trades.csv` — ranked results
- `{job_id}_top_trades_chart.png` — horizontal bar chart of top 20 trades

### Multi-ticker screening
Run one job per ticker, then aggregate with `screener_summary.csv`

---

## Implementation Phases

| Phase | Task | Files |
|---|---|---|
| A | Infrastructure (copy/trim/create base) | data_loader, stamper, config, result, batch, CLI |
| B | Bernstein composite chart | bernstein_chart.py |
| C | Best trade scanner | best_trade.py |
| D | Templates + smoke tests | templates/*.csv |

---

## Config CSV columns

### bernstein_batch_minimal.csv (composite charts)
`job_id, ticker, chart_mode, interval, start_year, end_year, win_rate_arrow_threshold, output_path, notes`

### best_trade_batch.csv (trade scanner)
`job_id, ticker, chart_mode, interval, start_year, end_year, min_years, win_rate_threshold, profit_factor_threshold, output_path, notes`
