#!/usr/bin/env python3
"""
Batch CSV Generator
====================
Generates a batch_cli.py input CSV by combining a tickers file with a model CSV.

The model CSV contains one or more rows, each defining a chart configuration
(chart type, y-axis metric, date range, etc.). Every ticker gets one output row
per model row, with the ticker substituted in and a unique job_id generated.

Usage:
    python templates/generate_batch.py tickers.txt model.csv
    python templates/generate_batch.py tickers.txt model.csv --output output/run.csv
    python templates/generate_batch.py tickers.txt model.csv --dry-run

Model CSV tips:
    - The ticker column in the model is just a placeholder — it gets replaced.
    - The model job_id becomes a suffix: {ticker_slug}_{model_job_id}
      Example: model job_id = "monthly_wr" + ticker "SPY" → "spy_monthly_wr"
    - Use {ticker} in output_path or notes for per-ticker substitution:
        output_path = output/{ticker}/
        notes       = {ticker} monthly win rate analysis
    - Set save_metadata=false to skip the JSON metadata file (only PNG saved).
      Set save_metadata=true to also save a {job_id}_metadata.json alongside the chart.

Examples:
    python templates/generate_batch.py templates/seasonality_cli/tickers_sample.txt templates/seasonality_cli/cli_model_v1.csv
    python templates/generate_batch.py templates/sp500_tickers.csv templates/seasonality_cli/cli_model_v1.csv --output output/generated_batch.csv --dry-run
"""

import argparse
import csv
import re
import sys
from pathlib import Path


def load_tickers(path: str) -> list:
    """Load tickers from file. One per line, blank lines and # comments ignored.
    A leading 'ticker' header line (case-insensitive) is automatically skipped,
    so both plain text files and CSV files with a 'ticker' column header work.
    """
    tickers = []
    with open(path, newline='', encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            line = line.split('#')[0].strip()   # strip inline comments
            if not line:
                continue
            ticker = line.upper()
            if ticker == 'TICKER':              # skip CSV header row
                continue
            tickers.append(ticker)
    return tickers


def slugify(ticker: str) -> str:
    """Make a ticker safe for use in a job_id: lowercase, non-alphanumeric → underscore."""
    return re.sub(r'[^a-z0-9]+', '_', ticker.lower()).strip('_')


def load_model(path: str):
    """Load model CSV. Returns (fieldnames, rows). Skips blank rows."""
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return [], []
        fieldnames = list(reader.fieldnames)
        rows = [row for row in reader if any(v.strip() for v in row.values())]
    return fieldnames, rows


def generate_rows(tickers: list, model_rows: list, fieldnames: list) -> list:
    """
    Generate output rows: one per (ticker × model row).
    - Replaces the ticker column with the actual ticker.
    - Builds job_id as {ticker_slug}_{model_job_id}.
    - Substitutes {ticker} in output_path and notes.
    """
    output = []
    for ticker in tickers:
        slug = slugify(ticker)
        for row in model_rows:
            new_row = dict(row)

            # Replace ticker
            new_row['ticker'] = ticker

            # Build job_id
            model_job_id = row.get('job_id', 'job').strip()
            new_row['job_id'] = f"{slug}_{model_job_id}"

            # Substitute {ticker} placeholder in string columns
            for col in ('output_path', 'notes'):
                if col in new_row and new_row[col]:
                    new_row[col] = new_row[col].replace('{ticker}', ticker)

            output.append(new_row)
    return output


def write_csv(path: str, fieldnames: list, rows: list):
    """Write generated rows to a CSV file, creating parent dirs as needed."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description='Generate a batch_cli.py input CSV from a tickers file + model CSV.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('tickers', help='Tickers file (one ticker per line, or CSV with ticker column)')
    parser.add_argument('model',   help='Model CSV (one row per chart configuration)')
    parser.add_argument(
        '--output', '-o',
        default='output/generated_batch.csv',
        help='Output CSV path (default: output/generated_batch.csv)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview result without writing the file'
    )
    args = parser.parse_args()

    # --- Load tickers ---
    try:
        tickers = load_tickers(args.tickers)
    except FileNotFoundError:
        print(f"Error: tickers file not found: {args.tickers}", file=sys.stderr)
        sys.exit(1)

    if not tickers:
        print(f"Error: no tickers found in '{args.tickers}'", file=sys.stderr)
        sys.exit(1)

    # --- Load model ---
    try:
        fieldnames, model_rows = load_model(args.model)
    except FileNotFoundError:
        print(f"Error: model CSV not found: {args.model}", file=sys.stderr)
        sys.exit(1)

    if not model_rows:
        print(f"Error: no data rows found in '{args.model}'", file=sys.stderr)
        sys.exit(1)

    for col in ('job_id', 'ticker', 'chart_type'):
        if col not in fieldnames:
            print(f"Error: model CSV is missing required column '{col}'", file=sys.stderr)
            sys.exit(1)

    # --- Generate ---
    rows = generate_rows(tickers, model_rows, fieldnames)
    n_tickers = len(tickers)
    n_configs = len(model_rows)
    n_total   = len(rows)

    print(f"Tickers      : {n_tickers}")
    print(f"Chart configs: {n_configs}  (model rows)")
    print(f"Total jobs   : {n_total}  ({n_tickers} × {n_configs})")

    if args.dry_run:
        preview = rows[:6]
        print(f"\nDry run — first {len(preview)} job_ids:")
        for r in preview:
            print(f"  {r['job_id']:<35}  ticker={r['ticker']}  chart={r.get('chart_type','')}")
        if n_total > len(preview):
            print(f"  ... and {n_total - len(preview)} more")
        print("\n(no file written)")
        return

    write_csv(args.output, fieldnames, rows)
    print(f"\nWritten to   : {args.output}")
    print(f"Next step    : python batch_cli.py {args.output}")


if __name__ == '__main__':
    main()
