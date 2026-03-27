"""
Batch processor — reads a CSV batch file and runs all jobs sequentially
or in parallel, collecting BernsteinResult objects.
"""

from __future__ import annotations
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .bernstein_config import BernsteinJobConfig, load_batch_csv
from .bernstein_result import BatchResults, BernsteinResult


def _run_single_job(cfg: BernsteinJobConfig) -> BernsteinResult:
    """Execute one job. Imported lazily to avoid circular imports in workers."""
    from .engine import BernsteinEngine
    engine = BernsteinEngine()
    return engine.run(cfg)


class BatchProcessor:
    """
    Reads a CSV batch file and executes all jobs.

    Usage:
        processor = BatchProcessor()
        results = processor.run(csv_path, workers=1, progress=True)
        results.save_summary("output/")
    """

    def run(
        self,
        csv_path: str,
        workers: int = 1,
        progress: bool = True,
    ) -> BatchResults:
        configs = load_batch_csv(csv_path)
        total = len(configs)

        if progress:
            print(f"Loaded {total} jobs from {csv_path}")

        if workers > 1:
            return self._run_parallel(configs, workers, progress)
        else:
            return self._run_sequential(configs, progress)

    # ── Sequential ────────────────────────────────────────────────────────────

    def _run_sequential(self, configs: list[BernsteinJobConfig],
                        progress: bool) -> BatchResults:
        batch = BatchResults()
        total = len(configs)

        for i, cfg in enumerate(configs, 1):
            if progress:
                print(f"  [{i}/{total}] {cfg.job_id} ({cfg.ticker}, {cfg.chart_type})",
                      end=" ... ", flush=True)
            t0 = time.time()
            result = _run_single_job(cfg)
            elapsed = time.time() - t0

            if result.success:
                saved = result.save_all(cfg.output_path)
                if progress:
                    print(f"OK  ({elapsed:.1f}s)  → {cfg.output_path}")
            else:
                if progress:
                    print(f"FAILED ({elapsed:.1f}s): {result.error_msg.splitlines()[0]}")

            batch.results.append(result)

        return batch

    # ── Parallel ──────────────────────────────────────────────────────────────

    def _run_parallel(self, configs: list[BernsteinJobConfig],
                      workers: int, progress: bool) -> BatchResults:
        batch = BatchResults()
        total = len(configs)
        done = 0

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_single_job, cfg): cfg for cfg in configs}
            for future in as_completed(futures):
                cfg = futures[future]
                done += 1
                try:
                    result = future.result()
                    if result.success:
                        result.save_all(cfg.output_path)
                except Exception as exc:
                    result = BernsteinResult.from_error(
                        cfg.job_id, cfg.ticker, cfg.chart_mode, exc
                    )

                if progress:
                    status = "OK" if result.success else "FAILED"
                    print(f"  [{done}/{total}] {cfg.job_id} — {status}")

                batch.results.append(result)

        return batch
