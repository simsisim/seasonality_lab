#!/usr/bin/env python3
"""
best_trade_cli.py — Phase 2: Best seasonal trade scanner.

Independently runnable. Has nothing to do with chart generation (Phase 1).

For each ticker, scans all (entry_doy, exit_doy) combinations and ranks
windows by Bernstein's criteria: win_rate, profit_factor, max_drawdown.

Output per ticker:
  {output_path}/{job_id}_best_trades.csv   ← ranked trade windows
  {output_path}/{job_id}_top20_chart.png   ← optional summary bar chart

Input CSV columns:
  job_id, ticker, ticker_file, start_year, end_year, exclude_years,
  min_years, win_rate_threshold, profit_factor_threshold, max_dd_threshold,
  top_n, save_chart, output_path, notes

Usage:
  python best_trade_cli.py user_input/jobs/best_trade_spy.csv
  python best_trade_cli.py user_input/jobs/best_trade_ndx100.csv --workers 4
  python best_trade_cli.py user_input/jobs/best_trade_spy.csv --no-chart
"""

import argparse
import sys
import time
import csv
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class BestTradeJobConfig:
    job_id: str = ""
    ticker: str = ""
    ticker_file: str = ""

    start_year: Optional[int] = None
    end_year: Optional[int] = None
    exclude_years: Optional[str] = None

    # Entry date scope — "11;12" = only Nov+Dec entries; "" = all months
    entry_months: str = ""

    # Window duration
    min_days_in_trade: int = 5
    max_days_in_trade: int = 45

    # Scanner thresholds (match Bernstein search_template.png)
    stop_pct: float = 9.0                  # Max Adverse Excursion % filter
    min_years: int = 15
    win_rate_threshold: float = 75.0       # % (not fraction)
    profit_factor_threshold: float = 1.5
    max_consec_losses: int = 999           # X Consecutive Losing Years filter
    direction: str = "long"               # long | short | all

    top_n: int = 20

    # Output
    save_chart: bool = True
    output_path: str = "output/best_trade/"
    notes: str = ""

    @property
    def excluded_years_list(self) -> list:
        if not self.exclude_years:
            return []
        return [int(y.strip()) for y in self.exclude_years.split(";") if y.strip()]


# ── CSV loader ────────────────────────────────────────────────────────────────

def _parse_int(v, default=None):
    v = str(v).strip()
    return int(v) if v else default

def _parse_float(v, default=0.0):
    v = str(v).strip()
    return float(v) if v else default

def _to_bool(v):
    return str(v).strip().lower() in {"true", "yes", "1"}


def load_best_trade_csv(csv_path: str) -> list:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with open(path, newline="", encoding="utf-8") as f:
        lines = [l for l in f if not l.strip().startswith("#") and l.strip()]

    reader = csv.DictReader(lines)
    configs = []

    for row in reader:
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        cfg = BestTradeJobConfig(
            job_id                  = row.get("job_id", ""),
            ticker                  = row.get("ticker", "").upper(),
            ticker_file             = row.get("ticker_file", ""),
            start_year              = _parse_int(row.get("start_year", "")),
            end_year                = _parse_int(row.get("end_year", "")),
            exclude_years           = row.get("exclude_years", ""),
            entry_months            = row.get("entry_months", ""),
            min_days_in_trade       = int(_parse_float(row.get("min_days_in_trade", ""), 5)),
            max_days_in_trade       = int(_parse_float(row.get("max_days_in_trade", ""), 45)),
            stop_pct                = _parse_float(row.get("stop_pct", ""), 9.0),
            min_years               = int(_parse_float(row.get("min_years", ""), 15)),
            win_rate_threshold      = _parse_float(row.get("win_rate_threshold", ""), 75.0),
            profit_factor_threshold = _parse_float(row.get("profit_factor_threshold", ""), 1.5),
            max_consec_losses       = int(_parse_float(row.get("max_consec_losses", ""), 999)),
            direction               = row.get("direction", "long").strip() or "long",
            top_n                   = int(_parse_float(row.get("top_n", ""), 20)),
            save_chart              = _to_bool(row.get("save_chart", "true")),
            output_path             = row.get("output_path", "output/best_trade/"),
            notes                   = row.get("notes", ""),
        )

        if cfg.ticker_file:
            configs.extend(_expand_ticker_file(cfg, path.parent))
        elif cfg.ticker:
            configs.append(cfg)

    return configs


def _expand_ticker_file(cfg, base_dir: Path) -> list:
    import copy
    ticker_path = Path(cfg.ticker_file)
    if not ticker_path.is_absolute():
        ticker_path = base_dir / ticker_path
    tickers = []
    for line in ticker_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.lower() == "ticker":
            continue
        tickers.append(line.upper())
    result = []
    for ticker in tickers:
        c = copy.copy(cfg)
        c.ticker = ticker
        c.ticker_file = ""
        c.job_id = f"{cfg.job_id}_{ticker}" if cfg.job_id else ticker
        result.append(c)
    return result


# ── Single job runner ─────────────────────────────────────────────────────────

def run_job(cfg: BestTradeJobConfig, save_chart: bool = True):
    """Run the best trade scan for one ticker. Returns (trades_df, figure_or_None)."""
    from datetime import date
    from src.data.data_loader import DataLoader
    from src.core.stamper import stamp_data
    from src.core.best_trade import run_best_trade_scan, draw_top_trades_chart

    loader = DataLoader(cache_dir="data/cache")
    start_dt = date(cfg.start_year, 1, 1) if cfg.start_year else None
    end_dt   = date(cfg.end_year, 12, 31) if cfg.end_year  else None

    df, _, _, _ = loader.load_symbol_data(
        symbol=cfg.ticker, source="yahoo",
        start_date=start_dt, end_date=end_dt, interval="1d"
    )
    df = stamp_data(df)

    if cfg.start_year:
        df = df[df["year"] >= cfg.start_year]
    if cfg.end_year:
        df = df[df["year"] <= cfg.end_year]
    if cfg.excluded_years_list:
        df = df[~df["year"].isin(cfg.excluded_years_list)]

    trades_df = run_best_trade_scan(
        df,
        ticker                      = cfg.ticker,
        entry_months                = cfg.entry_months,
        min_days_in_trade           = cfg.min_days_in_trade,
        max_days_in_trade           = cfg.max_days_in_trade,
        stop_pct                    = cfg.stop_pct,
        min_years                   = cfg.min_years,
        win_rate_threshold          = cfg.win_rate_threshold,
        profit_factor_threshold     = cfg.profit_factor_threshold,
        max_consec_losses_threshold = cfg.max_consec_losses,
        direction                   = cfg.direction,
    )

    fig = None
    if save_chart and cfg.save_chart and len(trades_df) > 0:
        fig = draw_top_trades_chart(trades_df, cfg.ticker, top_n=cfg.top_n)

    return trades_df, fig


def save_results(cfg: BestTradeJobConfig, trades_df, fig):
    out = Path(cfg.output_path)
    out.mkdir(parents=True, exist_ok=True)
    paths = []

    csv_path = out / f"{cfg.job_id}_best_trades.csv"
    trades_df.to_csv(str(csv_path), index=False)
    paths.append(str(csv_path))

    if fig is not None:
        png_path = out / f"{cfg.job_id}_top{cfg.top_n}_chart.png"
        fig.savefig(str(png_path), dpi=150, bbox_inches="tight")
        paths.append(str(png_path))

    return paths


# ── Batch runner ──────────────────────────────────────────────────────────────

def run_batch(configs, workers=1, progress=True, save_chart=True):
    results = []
    total = len(configs)

    for i, cfg in enumerate(configs, 1):
        if progress:
            print(f"  [{i}/{total}] {cfg.job_id} ({cfg.ticker})", end=" ... ", flush=True)
        t0 = time.time()
        try:
            trades_df, fig = run_job(cfg, save_chart=save_chart)
            saved = save_results(cfg, trades_df, fig)
            elapsed = time.time() - t0
            if progress:
                print(f"OK  ({elapsed:.1f}s)  {len(trades_df)} trades found")
            results.append({"job_id": cfg.job_id, "ticker": cfg.ticker,
                            "success": True, "n_trades": len(trades_df)})
        except Exception as exc:
            elapsed = time.time() - t0
            if progress:
                print(f"FAILED ({elapsed:.1f}s): {exc}")
            results.append({"job_id": cfg.job_id, "ticker": cfg.ticker,
                            "success": False, "error": str(exc)})

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Best seasonal trade scanner (Phase 2 — independent of chart generation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("csv", help="Path to best_trade input CSV")
    parser.add_argument("--output", "-o", default=None,
                        help="Override output directory for all jobs")
    parser.add_argument("--workers", "-w", type=int, default=1,
                        help="Parallel workers (default: 1)")
    parser.add_argument("--no-chart", action="store_true",
                        help="Skip PNG chart, save CSV only")
    parser.add_argument("--quiet", "-q", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    configs = load_best_trade_csv(args.csv)

    if args.output:
        for cfg in configs:
            cfg.output_path = args.output

    print(f"Best Trade Scanner")
    print(f"  Input:   {args.csv}")
    print(f"  Jobs:    {len(configs)}")
    print(f"  Workers: {args.workers}")
    print()

    results = run_batch(
        configs,
        workers=args.workers,
        progress=not args.quiet,
        save_chart=not args.no_chart,
    )

    n_ok   = sum(1 for r in results if r["success"])
    n_fail = sum(1 for r in results if not r["success"])
    print(f"\nDone — {n_ok} succeeded, {n_fail} failed")

    if n_fail:
        for r in results:
            if not r["success"]:
                print(f"  FAILED: {r['job_id']} — {r.get('error', '')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
