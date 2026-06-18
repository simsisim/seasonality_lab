#!/usr/bin/env python3
"""
summary_cli.py — Pre-compute best seasonal windows per ticker.

For each ticker finds the best 1-month, 2-month and 3-month consecutive windows
across the full year (circular: Dec→Jan wraps). No quality filters — every ticker
gets a row so you can see its natural seasons regardless of quality.

Run once per year after the seasonal data download.

Output (one CSV per index):
    output/summary/{index}_best_windows.csv

Usage:
    python summary_cli.py
    python summary_cli.py --index sp500
    python summary_cli.py --index all --output output/summary/
"""

import argparse
import glob
import sys
from pathlib import Path

import pandas as pd


MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

INDICES = {
    "sp500":       "output/git_download/sp500",
    "ndx100":      "output/git_download/ndx100",
    "iwm1000":     "output/git_download/iwm1000",
    "russell3000": "output/git_download/russell3000",
}

_DATA_DIR = Path(__file__).parent


# ── Data loading ──────────────────────────────────────────────────────────────

def load_index(name: str, data_dir: Path) -> pd.DataFrame:
    folder = data_dir / INDICES[name]
    files = glob.glob(str(folder / "*_monthly_wr_*_stats.csv"))
    if not files:
        raise FileNotFoundError(f"No monthly stats in {folder}")

    rows = []
    for f in files:
        try:
            df = pd.read_csv(f)
            stem   = Path(f).stem
            ticker = stem.split("_monthly_wr_")[1].replace("_stats", "").upper()
            df["ticker"] = ticker
            rows.append(df)
        except Exception:
            continue

    return pd.concat(rows, ignore_index=True)


# ── Window scoring ────────────────────────────────────────────────────────────

def _monthly_score(mean: float, win_rate: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return (win_rate / 100.0) * (mean / std)


def _window_label(months: list[str]) -> str:
    if len(months) == 1:
        return months[0]
    return f"{months[0]}-{months[-1]}"


def _best_window(by_month: dict, n: int) -> dict:
    """Find the best n-consecutive-month window (circular) by composite score."""
    best = None

    for start_i in range(12):
        months = [MONTH_ORDER[(start_i + j) % 12] for j in range(n)]

        # Skip if any month is missing data
        if any(m not in by_month for m in months):
            continue

        rows    = [by_month[m] for m in months]
        scores  = [_monthly_score(r["mean"], r["win_rate"], r["std"]) for r in rows]
        avg_wr  = sum(r["win_rate"] for r in rows) / n
        tot_ret = sum(r["mean"]     for r in rows)
        score   = sum(scores) / n

        if best is None or score > best["score"]:
            best = {
                "period":  _window_label(months),
                "avg_wr%": round(avg_wr, 1),
                "ret%":    round(tot_ret, 2),
                "score":   round(score, 4),
            }

    return best or {"period": "", "avg_wr%": None, "ret%": None, "score": None}


# ── Per-ticker summary ────────────────────────────────────────────────────────

def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for ticker, grp in df.groupby("ticker"):
        by_month = {row["period"]: row for _, row in grp.iterrows()}
        min_count = int(min(r["count"] for r in by_month.values())) if by_month else 0

        w1 = _best_window(by_month, 1)
        w2 = _best_window(by_month, 2)
        w3 = _best_window(by_month, 3)

        records.append({
            "ticker":       ticker,
            "years":        min_count,
            "best_1m":      w1["period"],
            "1m_wr%":       w1["avg_wr%"],
            "1m_ret%":      w1["ret%"],
            "1m_score":     w1["score"],
            "best_2m":      w2["period"],
            "2m_wr%":       w2["avg_wr%"],
            "2m_ret%":      w2["ret%"],
            "2m_score":     w2["score"],
            "best_3m":      w3["period"],
            "3m_wr%":       w3["avg_wr%"],
            "3m_ret%":      w3["ret%"],
            "3m_score":     w3["score"],
        })

    return (pd.DataFrame(records)
              .sort_values("1m_score", ascending=False)
              .reset_index(drop=True))


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Pre-compute best 1/2/3-month seasonal windows per ticker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--index", "-i", default="all",
                   help="Index(es): sp500, ndx100, iwm1000, russell3000, all (default: all)")
    p.add_argument("--output", "-o", default="output/summary/",
                   help="Output directory (default: output/summary/)")
    p.add_argument("--data-dir", default=None,
                   help="Project root containing output/git_download/")
    return p.parse_args()


def main():
    args     = parse_args()
    root     = Path(args.data_dir) if args.data_dir else _DATA_DIR
    out_dir  = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.index.lower() == "all":
        index_names = list(INDICES.keys())
    else:
        index_names = [n.strip().lower() for n in args.index.split(",")]
        bad = [n for n in index_names if n not in INDICES]
        if bad:
            print(f"Unknown index: {bad}. Valid: {', '.join(INDICES)}, all")
            sys.exit(1)

    for name in index_names:
        try:
            df = load_index(name, root)
            n_tickers = df["ticker"].nunique()
            print(f"{name}: {n_tickers} tickers ...", end=" ", flush=True)

            summary = build_summary(df)

            csv_path = out_dir / f"{name}_best_windows.csv"
            summary.to_csv(str(csv_path), index=False)
            print(f"saved → {csv_path}")

        except FileNotFoundError as exc:
            print(f"\n  WARNING: {exc}")

    print("Done.")


if __name__ == "__main__":
    main()
