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
        print("\nFailed jobs:")
        for r in results.results:
            if not r.success:
                print(f"  {r.job_id}: {r.error_msg.splitlines()[0]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
