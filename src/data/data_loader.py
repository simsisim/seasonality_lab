"""
Data loader for cycle analysis dashboard.
Supports multiple data sources: Yahoo Finance, CSV files, and existing market_data directory.
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
    
    def __init__(self, market_data_path: str = None, cache_dir: str = "data/cache"):
        """
        Initialize data loader.
        
        Args:
            market_data_path: Path to existing market data directory
            cache_dir: Directory for caching downloaded data
        """
        self.market_data_path = Path(market_data_path) if market_data_path else None
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_symbol_data(self, symbol: str, source: str = "auto", start_date=None, end_date=None, interval: str = "1d") -> Tuple[pd.DataFrame, str, Optional[str], bool]:
        """
        Load data for a symbol from appropriate source.
        
        Args:
            symbol: Symbol ticker (e.g., "AAPL:yfi" or "AAPL")
            source: Data source ("auto", "yahoo", "csv", "market_data")
            start_date: Optional start date for historical data (datetime.date object)
            end_date: Optional end date for historical data (datetime.date object)
            interval: Data interval ("1d", "1wk", "1mo") - only for Yahoo Finance
            
        Returns:
            Tuple of (DataFrame, source_name, cache_filename_or_path, loaded_from_cache)
        """
        # Parse symbol for special suffixes
        if ":yfi" in symbol.lower():
            clean_symbol = symbol.split(":")[0]
            source = "yahoo"
        else:
            clean_symbol = symbol
        
        # Auto-determine source if needed
        if source == "auto":
            source = self._determine_source(clean_symbol)
        
        # Load from appropriate source
        if source == "yahoo":
            df, cache_file, from_cache = self._load_from_yahoo(clean_symbol, start_date=start_date, end_date=end_date, interval=interval)
            return df, "Yahoo Finance", cache_file, from_cache
        elif source == "market_data":
            df, file_path = self._load_from_market_data(clean_symbol, start_date=start_date)
            # Apply end_date filter if provided
            if end_date and 'timestamp' in df.columns:
                end_ts = pd.Timestamp(end_date).timestamp() + 86400  # Include end date
                df = df[df['timestamp'] <= end_ts]
            return df, "Market Data", str(file_path), False
        else:
            raise ValueError(f"Unknown data source: {source}")
    
    def _determine_source(self, symbol: str) -> str:
        """
        Automatically determine the best data source.
        
        Args:
            symbol: Symbol ticker
            
        Returns:
            Source name ("yahoo" or "market_data")
        """
        # If symbol has :yfi tag, use Yahoo Finance
        if ":yfi" in symbol:
            return "yahoo"
        
        # Check if symbol exists in market_data directory
        clean_symbol = symbol.replace(":yfi", "").strip().upper()
        if self.market_data_path and self._check_market_data_exists(clean_symbol):
            return "market_data"
        
        # Default to Yahoo Finance
        return "yahoo"
    
    def _check_market_data_exists(self, symbol: str) -> bool:
        """Check if symbol exists in market_data directory."""
        if not self.market_data_path or not self.market_data_path.exists():
            return False
        
        # Look for CSV files matching the symbol
        possible_files = [
            self.market_data_path / f"{symbol}.csv",
            self.market_data_path / f"{symbol}_data.csv",
            self.market_data_path / symbol / "data.csv",
        ]
        
        return any(f.exists() for f in possible_files)
    
    def _load_from_yahoo(self, symbol: str, start_date=None, end_date=None, interval: str = "1d") -> Tuple[pd.DataFrame, str, bool]:
        """
        Load data from Yahoo Finance.
        
        Args:
            symbol: Clean symbol ticker
            start_date: Optional start date (datetime.date object)
            end_date: Optional end date (datetime.date object)
            interval: Data interval ("1d", "1wk", "1mo")
            
        Returns:
            Tuple of (DataFrame, cache_filename, loaded_from_cache)
        """
        try:
            from datetime import date as date_type
            
            # Construct partial cache filename pattern for searching
            start_str = "MAX"
            if start_date and isinstance(start_date, date_type):
                start_str = start_date.strftime('%Y-%m-%d')
            
            safe_symbol = symbol.replace(":", "").replace("/", "")
            # Pattern: YFI_{symbol}_{interval}_{start_date}_*.csv
            cache_pattern = f"YFI_{safe_symbol}_{interval}_{start_str}_*.csv"
            
            # Check for existing cache files
            existing_files = list(self.cache_dir.glob(cache_pattern))
            if existing_files:
                # Sort by modification time (newest first)
                existing_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_cache = existing_files[0]
                
                # Check if cache is recent (less than 24 hours old)
                cache_age = datetime.now().timestamp() - latest_cache.stat().st_mtime
                if cache_age < 86400:  # 24 hours
                    df = pd.read_csv(latest_cache, index_col=0)
                    # Apply end_date filter to cached data
                    if end_date and 'timestamp' in df.columns:
                        end_ts = pd.Timestamp(end_date).timestamp() + 86400
                        df = df[df['timestamp'] <= end_ts]
                    return df, latest_cache.name, True
            
            # Download from Yahoo Finance
            ticker = yf.Ticker(symbol)
            
            # Build download parameters
            if start_date and isinstance(start_date, date_type):
                start_str_yf = start_date.strftime('%Y-%m-%d')
                if end_date and isinstance(end_date, date_type):
                    end_str_yf = end_date.strftime('%Y-%m-%d')
                    df = ticker.history(start=start_str_yf, end=end_str_yf, interval=interval)
                else:
                    df = ticker.history(start=start_str_yf, interval=interval)
            else:
                df = ticker.history(period="max", interval=interval)
                # Apply end_date filter after download if provided
                if end_date and isinstance(end_date, date_type):
                    end_ts = pd.Timestamp(end_date)
                    if df.index.tz is not None:
                        end_ts = end_ts.tz_localize(df.index.tz)
                    df = df[df.index <= end_ts]
            
            if df.empty:
                raise ValueError(f"No data found for symbol: {symbol}")
            
            # Standardize column names
            df = self._standardize_dataframe(df)
            
            # Determine end date from data
            last_ts = df['timestamp'].max()
            last_date = pd.to_datetime(last_ts, unit='s').date()
            end_str = last_date.strftime('%Y-%m-%d')
            
            # Generate final filename with end date
            cache_filename = f"YFI_{safe_symbol}_{interval}_{start_str}_{end_str}.csv"
            cache_file = self.cache_dir / cache_filename
            
            # Cache the data
            df.to_csv(cache_file)
            
            return df, cache_filename, False
            
        except Exception as e:
            raise ValueError(f"Failed to load data from Yahoo Finance for {symbol}: {str(e)}")
    
    def _load_from_market_data(self, symbol: str, start_date=None) -> Tuple[pd.DataFrame, Path]:
        """
        Load data from market_data directory.
        
        Args:
            symbol: Symbol ticker
            start_date: Optional start date to filter data (datetime.date object)
            
        Returns:
            Tuple of (DataFrame, file_path)
        """
        if not self.market_data_path:
            raise ValueError("Market data path not configured")
        
        # Look for CSV file
        data_file = self.market_data_path / f"{symbol}.csv"
        
        if not data_file.exists():
            raise ValueError(f"Data file not found in market_data: {symbol}.csv")
        
        try:
            df = pd.read_csv(data_file, index_col=0, parse_dates=True)
            
            # Standardize format
            df = self._standardize_dataframe(df)
            
            # Filter by start_date if provided
            if start_date:
                from datetime import datetime as dt
                start_timestamp = dt.combine(start_date, dt.min.time()).timestamp()
                df = df[df['timestamp'] >= start_timestamp]
            
            return df, data_file
            
        except Exception as e:
            raise ValueError(f"Failed to load data from market_data for {symbol}: {str(e)}")
    
    def load_from_csv(self, file_path: str) -> pd.DataFrame:
        """
        Load data from custom CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            DataFrame with OHLCV data

        Note:
            Supports multiple formats:
            1. Standard: 'time' and 'close' columns
            2. Simple X,Y format: sequential index and values
        """
        df = pd.read_csv(file_path)

        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()

        # Check for simple X,Y format (common in synthetic/research datasets)
        if 'x' in df.columns and 'y' in df.columns:
            # X,Y format: X is sequential index, Y is the value
            df = df.rename(columns={'y': 'close'})

            # Create synthetic timestamp from X (sequential bars)
            # Start from a base date (2020-01-01) and add X days
            base_timestamp = pd.Timestamp('2020-01-01').timestamp()
            df['timestamp'] = base_timestamp + df['x'] * 86400  # 86400 seconds per day

            # Add optional columns
            df['open'] = None
            df['high'] = None
            df['low'] = None
            df['volume'] = None

            # Select columns in standard order
            result = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            return result

        # Standard format validation
        if 'close' not in df.columns:
            raise ValueError("CSV must contain 'close' column (or X,Y format)")

        df = self._standardize_dataframe(df)

        return df
    
    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame format.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Standardized DataFrame with columns: timestamp, open, high, low, close, volume
        """
        # Create a copy
        df = df.copy()
        
        # Normalize column names (lowercase)
        df.columns = df.columns.str.lower().str.strip()
        
        # Handle different time column names
        time_columns = ['time', 'date', 'datetime', 'timestamp']
        time_col = None
        for col in time_columns:
            if col in df.columns:
                time_col = col
                break
        
        # Convert index to timestamp if it's datetime
        if isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = df.index.astype(np.int64) // 10**9  # Convert to Unix timestamp
        elif time_col:
            # Check if it's sequential bar indices (0, 1, 2, ...) rather than real timestamps
            # This is common in synthetic/research datasets
            if df[time_col].dtype in [np.int64, np.int32, np.float64]:
                # Check if values are small sequential numbers (likely bar indices)
                min_val = df[time_col].min()
                max_val = df[time_col].max()

                # If values start near 0 and are sequential, treat as bar indices
                if min_val >= 0 and max_val < 100000:  # Arbitrary threshold
                    # Create synthetic timestamps: start from 2020-01-01, add one day per bar
                    base_timestamp = pd.Timestamp('2020-01-01').timestamp()
                    df['timestamp'] = base_timestamp + df[time_col].astype(int) * 86400  # 86400 sec/day
                else:
                    # Large integers - treat as Unix timestamps
                    df['timestamp'] = df[time_col].astype(np.int64)
            else:
                # Parse as datetime string
                df['timestamp'] = pd.to_datetime(df[time_col])
                df['timestamp'] = df['timestamp'].astype(np.int64) // 10**9
        else:
            raise ValueError("No time/date column found in data")
        
        # Ensure required columns exist
        required_cols = ['close']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in data")
        
        # Optional columns (set to None if missing)
        optional_cols = ['open', 'high', 'low', 'volume']
        for col in optional_cols:
            if col not in df.columns:
                df[col] = None
        
        # Select and order columns
        result = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        # Sort by timestamp
        result = result.sort_values('timestamp')
        
        # Remove duplicates
        result = result.drop_duplicates(subset=['timestamp'], keep='last')
        
        # Reset index
        result = result.reset_index(drop=True)
        
        return result
    
    def get_available_symbols(self) -> List[str]:
        """
        Get list of available symbols from market_data directory.
        
        Returns:
            List of symbol tickers
        """
        if not self.market_data_path or not self.market_data_path.exists():
            return []
        
        symbols = []
        
        # Look for CSV files
        for file in self.market_data_path.glob("*.csv"):
            # Remove .csv extension and _data suffix
            symbol = file.stem.replace("_data", "")
            symbols.append(symbol)
        
        # Look for subdirectories with data.csv
        for directory in self.market_data_path.iterdir():
            if directory.is_dir():
                data_file = directory / "data.csv"
                if data_file.exists():
                    symbols.append(directory.name)
        
        return sorted(list(set(symbols)))
    
    # ========================================================================
    # RESAMPLING FUNCTIONS (for multi-timeframe analysis)
    # ========================================================================
    
    @staticmethod
    def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
        """
        Resample daily data to weekly (Friday close).
        
        Args:
            df: DataFrame with timestamp, open, high, low, close, volume
        
        Returns:
            Weekly resampled DataFrame
        """
        df = df.copy()
        
        # Convert timestamp to datetime index
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.set_index('datetime')
        
        # Resample to weekly (Week ending Friday)
        weekly = df.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna(subset=['close'])
        
        # Convert back to timestamp format
        weekly['timestamp'] = weekly.index.astype(np.int64) // 10**9
        weekly = weekly.reset_index(drop=True)
        
        # Reorder columns
        return weekly[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    @staticmethod
    def resample_to_monthly(df: pd.DataFrame) -> pd.DataFrame:
        """
        Resample daily data to monthly (month-end close).
        
        Args:
            df: DataFrame with timestamp, open, high, low, close, volume
        
        Returns:
            Monthly resampled DataFrame
        """
        df = df.copy()
        
        # Convert timestamp to datetime index
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.set_index('datetime')
        
        # Resample to monthly (Month end)
        monthly = df.resample('M').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna(subset=['close'])
        
        # Convert back to timestamp format
        monthly['timestamp'] = monthly.index.astype(np.int64) // 10**9
        monthly = monthly.reset_index(drop=True)
        
        # Reorder columns
        return monthly[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

