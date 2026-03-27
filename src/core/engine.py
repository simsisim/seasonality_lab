"""
BernsteinEngine — orchestrates a single job end-to-end.

Routes chart_mode to the appropriate sub-module:
  "composite"  → bernstein_chart.generate_bernstein_chart()
  "best_trade" → best_trade.run_best_trade_scan()
"""

from __future__ import annotations
from datetime import date
from pathlib import Path
import sys

import pandas as pd

from .bernstein_config import BernsteinJobConfig
from .bernstein_result import BernsteinResult


class BernsteinEngine:

    def __init__(self, cache_dir: str = "data/cache"):
        self._cache_dir = cache_dir

    def run(self, cfg: BernsteinJobConfig) -> BernsteinResult:
        try:
            df = self._load(cfg)
            df = self._filter_years(df, cfg)

            if cfg.chart_type == "Bernstein Composite":
                return self._run_composite(df, cfg)
            elif cfg.chart_type == "Best Trade":
                return self._run_best_trade(df, cfg)
            else:
                return self._run_legacy(df, cfg)

        except Exception as exc:
            return BernsteinResult.from_error(cfg.job_id, cfg.ticker, cfg.chart_type, exc)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load(self, cfg: BernsteinJobConfig) -> pd.DataFrame:
        from ..data.data_loader import DataLoader
        from .stamper import stamp_data

        loader = DataLoader(cache_dir=self._cache_dir)

        start_dt = date(cfg.start_year, 1, 1) if cfg.start_year else None
        end_dt   = date(cfg.end_year,  12, 31) if cfg.end_year  else None

        df, source, cache_file, from_cache = loader.load_symbol_data(
            symbol     = cfg.ticker,
            source     = cfg.data_source,
            start_date = start_dt,
            end_date   = end_dt,
            interval   = cfg.interval,
        )

        df = stamp_data(df)
        return df

    # ── Year filtering ────────────────────────────────────────────────────────

    def _filter_years(self, df: pd.DataFrame, cfg: BernsteinJobConfig) -> pd.DataFrame:
        if cfg.start_year:
            df = df[df['year'] >= cfg.start_year]
        if cfg.end_year:
            df = df[df['year'] <= cfg.end_year]
        if cfg.excluded_years_list:
            df = df[~df['year'].isin(cfg.excluded_years_list)]
        return df

    # ── Composite chart ───────────────────────────────────────────────────────

    def _run_composite(self, df: pd.DataFrame, cfg: BernsteinJobConfig) -> BernsteinResult:
        from .bernstein_chart import generate_bernstein_chart

        fig, composite_df = generate_bernstein_chart(df, cfg)

        result = BernsteinResult(
            job_id=cfg.job_id,
            ticker=cfg.ticker,
            chart_mode=cfg.chart_type,
            figure=fig,
            tables={"composite": composite_df},
            metadata={
                "ticker": cfg.ticker,
                "start_year": cfg.start_year,
                "end_year": cfg.end_year,
            },
        )
        return result

    # ── Legacy chart types ────────────────────────────────────────────────────

    def _run_legacy(self, df: pd.DataFrame, cfg: BernsteinJobConfig) -> BernsteinResult:
        from .legacy_charts import generate_legacy_chart

        fig, stats_df = generate_legacy_chart(df, cfg)

        return BernsteinResult(
            job_id=cfg.job_id,
            ticker=cfg.ticker,
            chart_mode=cfg.chart_type,
            figure=fig,
            tables={"stats": stats_df},
            metadata={"ticker": cfg.ticker, "chart_type": cfg.chart_type},
        )

    # ── Best trade scanner ────────────────────────────────────────────────────

    def _run_best_trade(self, df: pd.DataFrame, cfg: BernsteinJobConfig) -> BernsteinResult:
        from .best_trade import run_best_trade_scan, draw_top_trades_chart

        trades_df = run_best_trade_scan(
            df,
            min_years               = cfg.min_years,
            win_rate_threshold      = cfg.win_rate_threshold,
            profit_factor_threshold = cfg.profit_factor_threshold,
            max_dd_threshold        = cfg.max_dd_threshold,
        )

        fig = draw_top_trades_chart(trades_df, cfg.ticker, top_n=20)

        result = BernsteinResult(
            job_id=cfg.job_id,
            ticker=cfg.ticker,
            chart_mode=cfg.chart_type,
            figure=fig,
            tables={"best_trades": trades_df},
            metadata={"ticker": cfg.ticker, "n_trades_found": len(trades_df)},
        )
        return result
