#!/usr/bin/env python3
"""
screener_cli.py — Seasonal top-performer screener.

Reads pre-computed monthly stats from output/git_download/ and ranks tickers
by seasonal quality for a target month window (default: next 2 months).

Score = avg(win_rate/100 × mean/std)  across target months × confidence(count)

Usage:
    python screener_cli.py
    python screener_cli.py --index sp500,ndx100 --months Jul,Aug
    python screener_cli.py --index all --months Jul --min-win-rate 65 --top 50
    python screener_cli.py --index sp500,ndx100 --months Jul,Aug --highlight AMD,DELL
    python screener_cli.py --index sp500,ndx100 --lookup AMD,DELL
    python screener_cli.py --index sp500 --months Jul,Aug,Sep -o output/screener/
"""

import argparse
import glob
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from tabulate import tabulate


MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

INDICES = {
    "sp500":       "output/git_download/sp500",
    "ndx100":      "output/git_download/ndx100",
    "iwm1000":     "output/git_download/iwm1000",
    "russell3000": "output/git_download/russell3000",
}

_DATA_DIR = Path(__file__).parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_months(n: int = 2) -> list[str]:
    m = date.today().month
    return [MONTH_ORDER[(m - 1 + i) % 12] for i in range(1, n + 1)]


def _monthly_score(mean: float, win_rate: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return (win_rate / 100.0) * (mean / std)


def _streak_from(monthly_stats: dict, start_month: str,
                 min_wr: float, min_ret: float) -> list[str]:
    qualifying = {m for m, s in monthly_stats.items()
                  if s["win_rate"] >= min_wr and s["mean"] >= min_ret}
    start_i = MONTH_ORDER.index(start_month)
    streak = []
    for j in range(12):
        m = MONTH_ORDER[(start_i + j) % 12]
        if m in qualifying:
            streak.append(m)
        else:
            break
    return streak


# ── Lookup helpers ───────────────────────────────────────────────────────────

def _best_window(by_month: dict, n: int) -> dict:
    """Best n-consecutive-month window (circular) by avg composite score."""
    best = None
    for start_i in range(12):
        months = [MONTH_ORDER[(start_i + j) % 12] for j in range(n)]
        if any(m not in by_month for m in months):
            continue
        rows   = [by_month[m] for m in months]
        score  = sum(_monthly_score(r["mean"], r["win_rate"], r["std"]) for r in rows) / n
        avg_wr = sum(r["win_rate"] for r in rows) / n
        tot_ret = sum(r["mean"]    for r in rows)
        label  = months[0] if n == 1 else f"{months[0]}-{months[-1]}"
        if best is None or score > best["score"]:
            best = {"period": label, "avg_wr%": round(avg_wr, 1),
                    "ret%": round(tot_ret, 2), "score": round(score, 4)}
    return best or {"period": "—", "avg_wr%": None, "ret%": None, "score": None}


def print_lookup(df: pd.DataFrame, tickers: list[str]) -> None:
    """Print full monthly breakdown + best windows for each requested ticker."""
    for ticker in tickers:
        grp = df[df["ticker"] == ticker.upper()]
        if grp.empty:
            print(f"\n  {ticker}: not found in loaded data")
            continue

        by_month   = {row["period"]: row for _, row in grp.iterrows()}
        index_name = grp.iloc[0]["index"]
        years      = int(grp["count"].min())

        # All 12 months ranked by score
        rows = []
        for m in MONTH_ORDER:
            if m not in by_month:
                continue
            r     = by_month[m]
            score = _monthly_score(r["mean"], r["win_rate"], r["std"])
            rows.append({"month": m, "wr%": round(r["win_rate"], 1),
                         "ret%": round(r["mean"], 2), "score": round(score, 4)})

        monthly = (pd.DataFrame(rows)
                     .sort_values("score", ascending=False)
                     .reset_index(drop=True))
        monthly.index     = monthly.index + 1
        monthly.index.name = "rank"

        w1 = _best_window(by_month, 1)
        w2 = _best_window(by_month, 2)
        w3 = _best_window(by_month, 3)

        sep = "─" * 52
        print(f"\n{sep}")
        print(f"  {ticker}  ({index_name})  —  {years} years of data")
        print(sep)
        print(tabulate(monthly, headers="keys", tablefmt="simple", floatfmt=".2f"))
        print(f"\n  Best windows:")
        for w, label in [(w1, "1 month "), (w2, "2 months"), (w3, "3 months")]:
            if w["period"] != "—":
                print(f"    {label}  {w['period']:12s}  "
                      f"wr {w['avg_wr%']:5.1f}%   ret {w['ret%']:+6.2f}%   score {w['score']:.3f}")


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
            df["index"]  = name
            rows.append(df)
        except Exception:
            continue

    return pd.concat(rows, ignore_index=True)


# ── TradingView watchlist parser ─────────────────────────────────────────────

_US_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "CBOE", "NYSEARCA", "BATS"}


def parse_tv_watchlist(path: str) -> tuple[list[str], list[str]]:
    """
    Parse a TradingView watchlist export (.txt).
    Format: comma-separated, sections as ###NAME, tickers as EXCHANGE:SYMBOL.

    Returns (us_tickers, skipped) where:
      us_tickers — plain symbols from US exchanges, e.g. ["NVDA", "AMD"]
      skipped    — full "EXCHANGE:SYMBOL" strings for non-US entries
    """
    content = Path(path).read_text(encoding="utf-8").strip()
    parts   = [p.strip() for p in content.split(",") if p.strip()]

    us_tickers, skipped = [], []
    for part in parts:
        if part.startswith("###"):
            continue
        if ":" in part:
            exchange, symbol = part.split(":", 1)
            if exchange.upper() in _US_EXCHANGES:
                us_tickers.append(symbol.upper())
            else:
                skipped.append(part)
        else:
            us_tickers.append(part.upper())

    return us_tickers, skipped


# ── Scoring ───────────────────────────────────────────────────────────────────

def _ticker_record(by_month: dict, target_months: list[str],
                   min_win_rate: float, min_return: float, min_count: int,
                   ticker: str, index_name: str) -> tuple[dict | None, bool, str]:
    """
    Compute stats for one ticker.
    Returns (record_dict, passes_filter, failure_reason).
    Returns (None, False, reason) if data is missing for any target month.
    """
    for m in target_months:
        if m not in by_month:
            return None, False, f"no data for {m}"

    fails = []
    m_scores = {}
    for m in target_months:
        r = by_month[m]
        if r["count"] < min_count:
            fails.append(f"{m}: {int(r['count'])}yr < {min_count}yr")
        elif r["win_rate"] < min_win_rate:
            fails.append(f"{m}: wr {r['win_rate']:.0f}% < {min_win_rate:.0f}%")
        elif r["mean"] < min_return:
            fails.append(f"{m}: ret {r['mean']:.1f}% < {min_return:.1f}%")
        m_scores[m] = _monthly_score(r["mean"], r["win_rate"], r["std"])

    passes     = len(fails) == 0
    min_cnt    = min(by_month[m]["count"] for m in target_months)
    confidence = min(min_cnt / 15.0, 1.0)
    score      = sum(m_scores.values()) / len(target_months) * confidence

    streak = _streak_from(by_month, target_months[0], 60.0, 1.0)
    streak_label = (f"{streak[0]}→{streak[-1]}" if len(streak) > 1 else streak[0]) if streak else ""

    rec = {
        "ticker":     ticker,
        "index":      index_name,
        "years":      int(min_cnt),
        "score":      round(score, 4),
        "streak":     streak_label,
        "streak_len": len(streak),
    }
    for m in target_months:
        r = by_month[m]
        rec[f"{m}_wr%"]  = round(r["win_rate"], 1)
        rec[f"{m}_ret%"] = round(r["mean"], 2)

    return rec, passes, "; ".join(fails)


def score_tickers(
    df: pd.DataFrame,
    target_months: list[str],
    min_win_rate: float,
    min_return: float,
    min_count: int,
    highlight: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (filtered_ranked, highlighted_df).

    filtered_ranked  — tickers that pass all hard filters, ranked by score.
    highlighted_df   — one row per highlighted ticker (passes or not), with
                       universe_rank showing position among all tickers with data.
    """
    highlight = {t.upper() for t in (highlight or [])}

    all_records  = []
    fail_reasons = {}   # ticker → failure reason (for highlighted display)

    for ticker, grp in df.groupby("ticker"):
        by_month   = {row["period"]: row for _, row in grp.iterrows()}
        index_name = grp.iloc[0]["index"]

        rec, passes, reason = _ticker_record(
            by_month, target_months, min_win_rate, min_return, min_count,
            ticker, index_name,
        )
        if rec is None:
            if ticker in highlight:
                fail_reasons[ticker] = reason
            continue

        rec["passes_filter"] = passes
        all_records.append(rec)
        if not passes:
            fail_reasons[ticker] = reason

    if not all_records:
        return pd.DataFrame(), pd.DataFrame()

    # Full universe ranked by score (used to find universe rank of highlighted tickers)
    universe = (pd.DataFrame(all_records)
                .sort_values("score", ascending=False)
                .reset_index(drop=True))
    universe.index     = universe.index + 1
    universe.index.name = "universe_rank"

    # Filtered results (normal screener output)
    filtered = (universe[universe["passes_filter"]]
                .drop(columns=["passes_filter"])
                .reset_index(drop=True))
    filtered.index     = filtered.index + 1
    filtered.index.name = "rank"

    # Highlighted tickers
    n_universe = len(universe)
    hl_rows = []
    for ticker in highlight:
        match = universe[universe["ticker"] == ticker]
        if not match.empty:
            row = match.iloc[0].to_dict()
            row["universe_rank"]  = match.index[0]
            row["universe_total"] = n_universe
            row["note"]           = fail_reasons.get(ticker, "")
        else:
            row = {
                "ticker":         ticker,
                "universe_rank":  None,
                "universe_total": n_universe,
                "note":           fail_reasons.get(ticker, "not found in loaded data"),
            }
        hl_rows.append(row)

    highlighted_df = pd.DataFrame(hl_rows) if hl_rows else pd.DataFrame()

    return filtered, highlighted_df


# ── Display ───────────────────────────────────────────────────────────────────

def _display_cols(df: pd.DataFrame, target_months: list[str]) -> pd.DataFrame:
    cols = ["ticker", "index"]
    for m in target_months:
        cols += [f"{m}_wr%", f"{m}_ret%"]
    cols += ["streak", "years", "score"]
    return df[[c for c in cols if c in df.columns]]


def _print_highlighted(hl_df: pd.DataFrame, target_months: list[str],
                       filtered: pd.DataFrame):
    """Print the highlighted tickers section."""
    print("\n── Highlighted tickers ──────────────────────────────────────────")

    rows = []
    for _, row in hl_df.iterrows():
        ticker = row.get("ticker", "?")

        # Check if it made the filtered list and find its filtered rank
        if not filtered.empty and ticker in filtered["ticker"].values:
            filt_rank = filtered.index[filtered["ticker"] == ticker][0]
            rank_str  = f"rank {filt_rank}/{len(filtered)} (passed)"
        elif row.get("universe_rank") is not None:
            rank_str = f"rank {row['universe_rank']}/{row.get('universe_total','?')} in universe  [filtered out]"
        else:
            rank_str = "not found"

        display_row = {
            "ticker":     ticker,
            "index":      row.get("index", ""),
            "rank":       rank_str,
        }
        for m in target_months:
            wr_key  = f"{m}_wr%"
            ret_key = f"{m}_ret%"
            display_row[f"{m}_wr%"]  = row.get(wr_key,  "—")
            display_row[f"{m}_ret%"] = row.get(ret_key, "—")

        def _fmt(v):
            import math
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return "—"
            return v

        display_row["streak"] = _fmt(row.get("streak", ""))
        display_row["years"]  = _fmt(row.get("years",  ""))
        display_row["score"]  = _fmt(row.get("score",  ""))
        display_row["note"]   = row.get("note", "")

        rows.append(display_row)

    print(tabulate(rows, headers="keys", tablefmt="simple"))


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Seasonal top-performer screener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--index", "-i", default="sp500",
                   help="Index(es): sp500, ndx100, iwm1000, russell3000, all (comma-sep)")
    p.add_argument("--months", "-m", default=None,
                   help="Target months, e.g. Jul,Aug  (default: next 2 months from today)")
    p.add_argument("--min-win-rate", type=float, default=60.0,
                   help="Min win rate %% per target month (default: 60)")
    p.add_argument("--min-return", type=float, default=1.0,
                   help="Min mean return %% per target month (default: 1.0)")
    p.add_argument("--min-count", type=int, default=5,
                   help="Min years of data per month (default: 5)")
    p.add_argument("--top", type=int, default=30,
                   help="Rows to show in terminal (default: 30)")
    p.add_argument("--highlight", default=None,
                   help="Comma-separated tickers to look up regardless of filters, e.g. AMD,DELL")
    p.add_argument("--lookup", default=None,
                   help="Show full monthly breakdown + best windows for specific tickers, e.g. AMD,DELL")
    p.add_argument("--watchlist", "-w", default=None,
                   help="TradingView watchlist .txt file — all US tickers become highlight + lookup targets")
    p.add_argument("--output", "-o", default=None,
                   help="Directory to save full ranked CSV (optional)")
    p.add_argument("--data-dir", default=None,
                   help="Project root containing output/git_download/ (default: script dir)")
    return p.parse_args()


def main():
    args  = parse_args()
    root  = Path(args.data_dir) if args.data_dir else _DATA_DIR

    # Indices
    if args.index.lower() == "all":
        index_names = list(INDICES.keys())
    else:
        index_names = [n.strip().lower() for n in args.index.split(",")]
        bad = [n for n in index_names if n not in INDICES]
        if bad:
            print(f"Unknown index: {bad}. Valid: {', '.join(INDICES)}, all")
            sys.exit(1)

    # Months
    if args.months:
        target_months = [m.strip().capitalize()[:3] for m in args.months.split(",")]
        bad = [m for m in target_months if m not in MONTH_ORDER]
        if bad:
            print(f"Unknown months: {bad}")
            sys.exit(1)
    else:
        target_months = _next_months(2)

    # Highlight / Lookup
    highlight = (set(t.strip().upper() for t in args.highlight.split(","))
                 if args.highlight else set())
    lookup = ([t.strip().upper() for t in args.lookup.split(",")]
              if args.lookup else [])

    # TradingView watchlist — merges into highlight + lookup
    if args.watchlist:
        wl_path = Path(args.watchlist)
        if not wl_path.exists():
            print(f"Watchlist not found: {wl_path}")
            sys.exit(1)
        wl_tickers, wl_skipped = parse_tv_watchlist(str(wl_path))
        highlight |= set(wl_tickers)
        lookup     = list(dict.fromkeys(lookup + wl_tickers))  # preserve order, no dupes
        print(f"  Watchlist : {wl_path.name}  →  {len(wl_tickers)} US tickers loaded")
        if wl_skipped:
            print(f"  Skipped   : {len(wl_skipped)} non-US tickers "
                  f"({', '.join(wl_skipped[:5])}{'...' if len(wl_skipped) > 5 else ''})")

    print("Seasonal Screener")
    print(f"  Indices : {', '.join(index_names)}")
    print(f"  Months  : {', '.join(target_months)}")
    print(f"  Filters : win_rate ≥ {args.min_win_rate}%  |  return ≥ {args.min_return}%  |  count ≥ {args.min_count}")
    if highlight:
        print(f"  Highlight: {', '.join(sorted(highlight))}")
    print()

    # Load
    dfs = []
    for name in index_names:
        try:
            idx_df = load_index(name, root)
            print(f"  {name:12s}  {idx_df['ticker'].nunique()} tickers")
            dfs.append(idx_df)
        except FileNotFoundError as exc:
            print(f"  WARNING: {exc}")

    if not dfs:
        print("No data found. Check --data-dir.")
        sys.exit(1)

    combined = (pd.concat(dfs, ignore_index=True)
                  .sort_values("count", ascending=False)
                  .drop_duplicates(subset=["ticker", "period"])
                  .reset_index(drop=True))
    print()

    # Score & rank
    ranked, hl_df = score_tickers(
        combined,
        target_months=target_months,
        min_win_rate=args.min_win_rate,
        min_return=args.min_return,
        min_count=args.min_count,
        highlight=highlight,
    )

    if ranked.empty and hl_df.empty:
        print("No tickers matched. Try lowering --min-win-rate or --min-return.")
        sys.exit(0)

    if not ranked.empty:
        n_total = len(ranked)
        n_show  = min(args.top, n_total)
        print(f"{n_total} qualifying tickers — showing top {n_show}:\n")
        display = _display_cols(ranked.head(n_show), target_months)
        print(tabulate(display, headers="keys", tablefmt="simple", floatfmt=".2f"))

        n_streak3 = (ranked["streak_len"] >= 3).sum()
        n_streak2 = (ranked["streak_len"] == 2).sum()
        print(f"\n  streak ≥3 months: {n_streak3}   |   streak = 2 months: {n_streak2}")
    else:
        print("No tickers passed the filters.")

    # Highlighted section
    if not hl_df.empty:
        _print_highlighted(hl_df, target_months, ranked)

    # Lookup — full monthly breakdown per ticker
    if lookup:
        print("\n")
        print_lookup(combined, lookup)

    # Save
    if args.output and not ranked.empty:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        months_tag  = "_".join(m.lower() for m in target_months)
        indices_tag = "+".join(index_names)
        csv_path = out_dir / f"screener_{months_tag}_{indices_tag}.csv"
        ranked.to_csv(str(csv_path))
        print(f"\n  Saved: {csv_path}  ({n_total} rows)")


if __name__ == "__main__":
    main()
