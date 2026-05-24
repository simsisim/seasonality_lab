"""
Data loader for cycle analysis dashboard.
Supports multiple data sources: Yahoo Finance, Stooq, local hist_data CSVs.

Source routing (set via ticker file column 2 or job CSV data_source column):
  auto / ""  → check hist_data/ first, fall back to Yahoo Finance
  yf         → Yahoo Finance only
  stooq      → auto-download from Stooq (cached)
  local      → hist_data/ only (hard error if file not found)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime
import yfinance as yf
import os


class DataLoader:
    """Handles data loading from multiple sources."""

    def __init__(self, cache_dir: str = "data/cache",
                 hist_data_path: str = None,
                 market_data_path: str = None):
        """
        Args:
            cache_dir:        Directory for caching downloaded data.
            hist_data_path:   Path to hist_data folder for manually saved CSVs.
            market_data_path: Legacy parameter (kept for backwards compat).
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hist_data_path = Path(hist_data_path) if hist_data_path else None
        self.market_data_path = Path(market_data_path) if market_data_path else None

    # ── Public entry point ────────────────────────────────────────────────────

    def load_symbol_data(self, symbol: str, source: str = "auto",
                         start_date=None, end_date=None,
                         interval: str = "1d") -> Tuple[pd.DataFrame, str, Optional[str], bool]:
        """
        Load data for a symbol from the appropriate source.

        Args:
            symbol:     Ticker symbol (e.g. "AAPL", "^DJI"). Append ":yfi" to force Yahoo.
            source:     "auto" | "yf" | "yahoo" | "stooq" | "local"
            start_date: Optional datetime.date – filter start.
            end_date:   Optional datetime.date – filter end.
            interval:   "1d" | "1wk" | "1mo"  (Yahoo / Stooq only)

        Returns:
            (DataFrame, source_label, cache_file_or_path, loaded_from_cache)
        """
        # Strip inline :yfi suffix
        if ":yfi" in symbol.lower():
            symbol = symbol.split(":")[0]
            source = "yf"

        source = (source or "auto").lower().strip()

        # Normalise aliases
        if source == "yahoo":
            source = "yf"

        if source == "auto":
            return self._load_auto(symbol, start_date, end_date, interval)
        elif source == "yf":
            df, cache_file, from_cache = self._load_from_yahoo(symbol, start_date, end_date, interval)
            return df, "Yahoo Finance", cache_file, from_cache
        elif source == "stooq":
            df, file_path, from_cache = self._load_from_stooq(symbol, start_date, end_date)
            return df, "Stooq (hist_data)", file_path, from_cache
        elif source == "local":
            df, file_path = self._load_from_hist_data(symbol, start_date, end_date)
            return df, "Local (hist_data)", str(file_path), False
        elif source == "market_data":
            # Legacy path
            df, file_path = self._load_from_market_data(symbol, start_date)
            if end_date and "timestamp" in df.columns:
                end_ts = pd.Timestamp(end_date).timestamp() + 86400
                df = df[df["timestamp"] <= end_ts]
            return df, "Market Data", str(file_path), False
        else:
            raise ValueError(f"Unknown data source: '{source}'. "
                             f"Valid values: auto, yf, stooq, local")

    # ── Auto routing ──────────────────────────────────────────────────────────

    def _load_auto(self, symbol, start_date, end_date, interval):
        """Check hist_data first; fall back to Yahoo Finance."""
        if self.hist_data_path and self._hist_data_exists(symbol):
            df, file_path = self._load_from_hist_data(symbol, start_date, end_date)
            return df, "Local (hist_data)", str(file_path), False
        df, cache_file, from_cache = self._load_from_yahoo(symbol, start_date, end_date, interval)
        return df, "Yahoo Finance", cache_file, from_cache

    # ── hist_data (local CSV) ─────────────────────────────────────────────────

    def _hist_data_exists(self, symbol: str) -> bool:
        if not self.hist_data_path or not self.hist_data_path.exists():
            return False
        return (self.hist_data_path / f"{symbol}.csv").exists()

    def _load_from_hist_data(self, symbol: str,
                             start_date=None,
                             end_date=None) -> Tuple[pd.DataFrame, Path]:
        """
        Load a manually saved CSV from hist_data/.
        Expected filename: {SYMBOL}.csv  (e.g. ^DJI.csv)
        Expected columns:  Date, Open, High, Low, Close, Volume  (any case)
        """
        if not self.hist_data_path:
            raise ValueError("hist_data_path not configured")

        file_path = self.hist_data_path / f"{symbol}.csv"
        if not file_path.exists():
            raise FileNotFoundError(
                f"No local data file for '{symbol}' in hist_data/.\n"
                f"Expected: {file_path}\n"
                f"Place a CSV with columns Date,Open,High,Low,Close,Volume there."
            )

        df = pd.read_csv(file_path)
        df = self._standardize_dataframe(df)

        if start_date:
            from datetime import datetime as dt
            start_ts = dt.combine(start_date, dt.min.time()).timestamp()
            df = df[df["timestamp"] >= start_ts]
        if end_date:
            from datetime import datetime as dt
            end_ts = dt.combine(end_date, dt.max.time()).timestamp()
            df = df[df["timestamp"] <= end_ts]

        return df, file_path

    # ── Stooq ─────────────────────────────────────────────────────────────────

    def _load_from_stooq(self, symbol: str,
                         start_date=None,
                         end_date=None) -> Tuple[pd.DataFrame, str, bool]:
        """
        Load Stooq data.

        Stooq blocks automated downloads (bot detection), so the workflow is:
          1. Download manually from https://stooq.com/q/d/?s=^dji  (select All, CSV)
          2. Save as  user_input/tickers/hist_data/{SYMBOL}.csv
          3. Use  source=stooq  in the ticker file — the loader reads from hist_data/

        If hist_data/{symbol}.csv exists it is used directly (no network call).
        If not, a clear error with instructions is raised.
        """
        # Check hist_data for the file
        if self._hist_data_exists(symbol):
            df, file_path = self._load_from_hist_data(symbol, start_date, end_date)
            return df, str(file_path), False

        # File not found — give actionable instructions
        stooq_sym = symbol.lower().replace("^", "%5E")
        hist_path = (self.hist_data_path / f"{symbol}.csv") if self.hist_data_path \
                    else Path("user_input/tickers/hist_data") / f"{symbol}.csv"
        raise FileNotFoundError(
            f"Stooq source selected for '{symbol}' but no local file found.\n"
            f"\n"
            f"Stooq blocks automated downloads — manual steps required:\n"
            f"  1. Open: https://stooq.com/q/d/?s={stooq_sym}\n"
            f"  2. Select range 'Max', format 'CSV', click Download\n"
            f"  3. Save the file as: {hist_path}\n"
            f"\n"
            f"After that, re-run — the loader will use the local file."
        )

    # ── Yahoo Finance ─────────────────────────────────────────────────────────

    def _load_from_yahoo(self, symbol: str, start_date=None, end_date=None,
                         interval: str = "1d") -> Tuple[pd.DataFrame, str, bool]:
        try:
            from datetime import date as date_type

            start_str = "MAX"
            if start_date and isinstance(start_date, date_type):
                start_str = start_date.strftime("%Y-%m-%d")

            safe_symbol = symbol.replace(":", "").replace("/", "")
            cache_pattern = f"YFI_{safe_symbol}_{interval}_{start_str}_*.csv"

            existing_files = list(self.cache_dir.glob(cache_pattern))
            if existing_files:
                existing_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_cache = existing_files[0]
                cache_age = datetime.now().timestamp() - latest_cache.stat().st_mtime
                if cache_age < 86400:
                    df = pd.read_csv(latest_cache, index_col=0)
                    if end_date and "timestamp" in df.columns:
                        end_ts = pd.Timestamp(end_date).timestamp() + 86400
                        df = df[df["timestamp"] <= end_ts]
                    return df, latest_cache.name, True

            ticker = yf.Ticker(symbol)

            if start_date and isinstance(start_date, date_type):
                start_str_yf = start_date.strftime("%Y-%m-%d")
                if end_date and isinstance(end_date, date_type):
                    df = ticker.history(start=start_str_yf,
                                        end=end_date.strftime("%Y-%m-%d"),
                                        interval=interval)
                else:
                    df = ticker.history(start=start_str_yf, interval=interval)
            else:
                df = ticker.history(period="max", interval=interval)
                if end_date and isinstance(end_date, date_type):
                    end_ts = pd.Timestamp(end_date)
                    if df.index.tz is not None:
                        end_ts = end_ts.tz_localize(df.index.tz)
                    df = df[df.index <= end_ts]

            if df.empty:
                raise ValueError(f"No data found for symbol: {symbol}")

            df = self._standardize_dataframe(df)

            last_date = pd.to_datetime(df["timestamp"].max(), unit="s").date()
            end_str   = last_date.strftime("%Y-%m-%d")
            cache_filename = f"YFI_{safe_symbol}_{interval}_{start_str}_{end_str}.csv"
            cache_file = self.cache_dir / cache_filename
            df.to_csv(cache_file)

            return df, cache_filename, False

        except Exception as e:
            raise ValueError(f"Failed to load data from Yahoo Finance for {symbol}: {e}")

    # ── Legacy market_data ────────────────────────────────────────────────────

    def _load_from_market_data(self, symbol: str, start_date=None) -> Tuple[pd.DataFrame, Path]:
        if not self.market_data_path:
            raise ValueError("market_data_path not configured")

        data_file = self.market_data_path / f"{symbol}.csv"
        if not data_file.exists():
            raise ValueError(f"Data file not found in market_data: {symbol}.csv")

        df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        df = self._standardize_dataframe(df)

        if start_date:
            from datetime import datetime as dt
            start_ts = dt.combine(start_date, dt.min.time()).timestamp()
            df = df[df["timestamp"] >= start_ts]

        return df, data_file

    # ── Standardisation ───────────────────────────────────────────────────────

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.str.lower().str.strip()

        time_columns = ["time", "date", "datetime", "timestamp"]
        time_col = None
        for col in time_columns:
            if col in df.columns:
                time_col = col
                break

        if isinstance(df.index, pd.DatetimeIndex):
            # pandas 3.0: astype(np.int64) may return seconds instead of nanoseconds.
            # Normalise: convert to UTC, strip tz, cast to datetime64[s], then int64
            # to get reliable Unix seconds across all pandas versions.
            if df.index.tz:
                naive = df.index.tz_convert("UTC").tz_localize(None)
            else:
                naive = df.index
            df["timestamp"] = naive.astype("datetime64[s]").astype(np.int64)
        elif time_col:
            if df[time_col].dtype in [np.int64, np.int32, np.float64]:
                min_val, max_val = df[time_col].min(), df[time_col].max()
                if min_val >= 0 and max_val < 100000:
                    base = pd.Timestamp("2020-01-01").timestamp()
                    df["timestamp"] = base + df[time_col].astype(int) * 86400
                else:
                    df["timestamp"] = df[time_col].astype(np.int64)
            else:
                df["timestamp"] = pd.to_datetime(df[time_col])
                df["timestamp"] = df["timestamp"].astype(np.int64) // 10**9
        else:
            raise ValueError("No time/date column found in data")

        if "close" not in df.columns:
            raise ValueError("Required column 'close' not found in data")

        for col in ["open", "high", "low", "volume"]:
            if col not in df.columns:
                df[col] = None

        result = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        result = result.sort_values("timestamp")
        result = result.drop_duplicates(subset=["timestamp"], keep="last")
        result = result.reset_index(drop=True)
        return result

    # ── CSV loader (custom file path) ─────────────────────────────────────────

    def load_from_csv(self, file_path: str) -> pd.DataFrame:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.lower().str.strip()

        if "x" in df.columns and "y" in df.columns:
            df = df.rename(columns={"y": "close"})
            base = pd.Timestamp("2020-01-01").timestamp()
            df["timestamp"] = base + df["x"] * 86400
            df["open"] = df["high"] = df["low"] = df["volume"] = None
            return df[["timestamp", "open", "high", "low", "close", "volume"]].copy()

        if "close" not in df.columns:
            raise ValueError("CSV must contain 'close' column (or X,Y format)")

        return self._standardize_dataframe(df)

    # ── Resampling ────────────────────────────────────────────────────────────

    @staticmethod
    def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.set_index("datetime")
        weekly = df.resample("W-FRI").agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}
        ).dropna(subset=["close"])
        weekly["timestamp"] = weekly.index.astype(np.int64) // 10**9
        weekly = weekly.reset_index(drop=True)
        return weekly[["timestamp", "open", "high", "low", "close", "volume"]]

    @staticmethod
    def resample_to_monthly(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.set_index("datetime")
        monthly = df.resample("ME").agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}
        ).dropna(subset=["close"])
        monthly["timestamp"] = monthly.index.astype(np.int64) // 10**9
        monthly = monthly.reset_index(drop=True)
        return monthly[["timestamp", "open", "high", "low", "close", "volume"]]

    # ── Symbol discovery (legacy) ─────────────────────────────────────────────

    def get_available_symbols(self) -> List[str]:
        if not self.market_data_path or not self.market_data_path.exists():
            return []
        symbols = [f.stem.replace("_data", "")
                   for f in self.market_data_path.glob("*.csv")]
        for d in self.market_data_path.iterdir():
            if d.is_dir() and (d / "data.csv").exists():
                symbols.append(d.name)
        return sorted(set(symbols))
