"""
BernsteinResult — lightweight result container.

Holds the matplotlib Figure and any tabular data produced by a job,
and handles saving them to disk.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import traceback

import pandas as pd

from .bernstein_config import FIGURE_DPI


@dataclass
class BernsteinResult:
    job_id:     str
    ticker:     str
    chart_mode: str
    success:    bool = True
    error_msg:  str  = ""

    # Produced by the job
    figure:     Optional[object] = None        # matplotlib Figure
    tables:     dict[str, pd.DataFrame] = field(default_factory=dict)
    metadata:   dict = field(default_factory=dict)

    # ── Saving ────────────────────────────────────────────────────────────────

    def save_all(self, output_dir: str) -> list[str]:
        """Save figure (PNG) and all tables (CSV). Returns list of saved paths."""
        saved = []
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if self.figure is not None:
            png_path = out / f"{self.job_id}_chart.png"
            self.figure.savefig(str(png_path), dpi=FIGURE_DPI, bbox_inches="tight")
            saved.append(str(png_path))

        for name, df in self.tables.items():
            csv_path = out / f"{self.job_id}_{name}.csv"
            df.to_csv(str(csv_path), index=False)
            saved.append(str(csv_path))

        return saved

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def from_error(cls, job_id: str, ticker: str, chart_mode: str,
                   exc: Exception) -> BernsteinResult:
        return cls(
            job_id=job_id,
            ticker=ticker,
            chart_mode=chart_mode,
            success=False,
            error_msg=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
        )


@dataclass
class BatchResults:
    results: list[BernsteinResult] = field(default_factory=list)

    @property
    def n_success(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if not r.success)

    def summary_df(self) -> pd.DataFrame:
        rows = []
        for r in self.results:
            rows.append({
                "job_id":     r.job_id,
                "ticker":     r.ticker,
                "chart_mode": r.chart_mode,
                "success":    r.success,
                "error_msg":  r.error_msg,
            })
        return pd.DataFrame(rows)

    def save_summary(self, output_dir: str) -> str:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "batch_summary.csv"
        self.summary_df().to_csv(str(path), index=False)
        return str(path)
