#!/usr/bin/env python3
"""
seasonality_cli.py — Entry point for the seasonality analysis program.

Usage:
    python seasonality_cli.py <batch_csv> [options]

Examples:
    python seasonality_cli.py templates/bernstein_batch_minimal.csv
    python seasonality_cli.py templates/best_trade_batch.csv --output output/scan/
    python seasonality_cli.py templates/best_trade_nasdaq100.csv --workers 4
"""

import argparse
import csv as csv_mod
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bernstein Seasonality — CSV-driven batch runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "csv",
        help="Path to batch CSV file",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Override output directory for all jobs (optional)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1 = sequential)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )
    return parser.parse_args()


def _suggest_removals(no_data_tickers: set, batch_csv_path: Path) -> None:
    """Print grouped suggestions for removing not-found tickers from their ticker files."""
    # Find ticker files referenced in the batch CSV
    ticker_files = set()
    with open(batch_csv_path, newline="", encoding="utf-8") as f:
        lines = [l for l in f if not l.strip().lstrip('"').startswith("#") and l.strip()]
    base_dir = batch_csv_path.parent
    for row in csv_mod.DictReader(lines):
        tf = (row.get("ticker_file") or "").strip()
        if tf:
            tf_path = Path(tf) if Path(tf).is_absolute() else base_dir / tf
            tf_resolved = tf_path.resolve()
            if tf_resolved.exists():
                ticker_files.add(tf_resolved)

    # Map each failed ticker to its file
    by_file: dict = {}
    for tf_path in sorted(ticker_files):
        for line in tf_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ticker = line.split(",")[0].strip().upper()
            if ticker in no_data_tickers:
                by_file.setdefault(tf_path, []).append(ticker)

    if by_file:
        print("\nSuggested removals from ticker files:")
        for tf_path, tickers in by_file.items():
            print(f"  {tf_path}:")
            for t in sorted(set(tickers)):
                print(f"    - {t}")


def main():
    args = parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    # Add src/ to path so imports work when running from project root
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    from src.core.bernstein_config import load_batch_csv
    from src.core.batch import BatchProcessor

    configs = load_batch_csv(str(csv_path))

    # Override output path if --output given
    if args.output:
        for cfg in configs:
            cfg.output_path = args.output

    print(f"Bernstein Seasonality")
    print(f"  Batch: {csv_path}")
    print(f"  Jobs:  {len(configs)}")
    print(f"  Mode:  {'parallel x' + str(args.workers) if args.workers > 1 else 'sequential'}")
    print()

    processor = BatchProcessor()
    results = processor.run(
        csv_path = str(csv_path),
        workers  = args.workers,
        progress = not args.quiet,
    )

    # Save summary to the first job's output dir (or override)
    summary_dir = args.output or (configs[0].output_path if configs else "output/")
    summary_path = results.save_summary(summary_dir)

    print()
    print(f"Done — {results.n_success} succeeded, {results.n_failed} failed")
    print(f"Summary: {summary_path}")

    if results.n_failed:
        no_data, real_errors = [], []
        for r in results.results:
            if not r.success:
                (no_data if "No data found for symbol" in r.error_msg else real_errors).append(r)

        if no_data:
            no_data_tickers = {r.ticker for r in no_data}
            print(f"\nSkipped {len(no_data)} job(s) — ticker not found on Yahoo Finance:")
            for r in no_data:
                print(f"  {r.job_id}: {r.ticker}")
            _suggest_removals(no_data_tickers, csv_path)

        if real_errors:
            print("\nFailed jobs (unexpected errors):")
            for r in real_errors:
                print(f"  {r.job_id}: {r.error_msg.splitlines()[0]}")
            sys.exit(1)


if __name__ == "__main__":
    main()
