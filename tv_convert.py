#!/usr/bin/env python3
"""
tv_convert.py — Convert TradingView watchlist exports to ticker CSV files.

Reads a TradingView watchlist .txt (format: ###SECTION,EXCHANGE:SYMBOL,...)
and writes a standard ticker CSV (header "ticker", one symbol per line)
compatible with seasonality_cli.py ticker_file references.

Non-US exchanges (GETTEX, TRADEGATE, etc.) are skipped by default.

Usage:
    python tv_convert.py user_input/tickers/Ioa_port.txt
    python tv_convert.py user_input/tickers/Ioa_port.txt -o user_input/tickers/Ioa_port.csv
    python tv_convert.py user_input/tickers/Ioa_port.txt --all-exchanges
"""

import argparse
import sys
from pathlib import Path


_US_EXCHANGES = {"NASDAQ", "NYSE", "AMEX", "CBOE", "NYSEARCA", "BATS"}


def convert(src: Path, dst: Path, us_only: bool = True) -> tuple[int, list[str]]:
    content = src.read_text(encoding="utf-8").strip()
    parts   = [p.strip() for p in content.split(",") if p.strip()]

    tickers, skipped = [], []
    for part in parts:
        if part.startswith("###"):
            continue
        if ":" in part:
            exchange, symbol = part.split(":", 1)
            if not us_only or exchange.upper() in _US_EXCHANGES:
                tickers.append(symbol.upper())
            else:
                skipped.append(part)
        else:
            tickers.append(part.upper())

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(["ticker"] + tickers) + "\n", encoding="utf-8")

    return len(tickers), skipped


def main():
    p = argparse.ArgumentParser(
        description="Convert TradingView watchlist .txt to ticker CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input", help="TradingView watchlist .txt file")
    p.add_argument("--output", "-o", default=None,
                   help="Output CSV path (default: same path, .txt replaced with .csv)")
    p.add_argument("--all-exchanges", action="store_true",
                   help="Include non-US exchanges (default: US only)")
    args = p.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"File not found: {src}")
        sys.exit(1)

    dst = Path(args.output) if args.output else src.with_suffix(".csv")

    n, skipped = convert(src, dst, us_only=not args.all_exchanges)
    print(f"Converted: {n} tickers  →  {dst}")
    if skipped:
        print(f"Skipped {len(skipped)} non-US: "
              f"{', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}")


if __name__ == "__main__":
    main()
