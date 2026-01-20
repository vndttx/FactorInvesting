import yfinance as yf
import pandas as pd
import numpy as np

class RRGCalculator:
    def __init__(self, tickers, benchmark, start_date, window=14):
        self.tickers = tickers
        self.benchmark = benchmark
        self.start_date = start_date
        self.window = window
        self.data = None
        self.rrg_history = None

    def fetch_data(self):
        """Fetches data from Yahoo Finance."""
        all_symbols = self.tickers + [self.benchmark]
        print(f"Fetching data for RRG: {all_symbols}")
        
        # auto_adjust=True returns 'Close' which is adjusted
        df = yf.download(all_symbols, start=self.start_date, progress=False, auto_adjust=True)
        
        # Handle MultiIndex columns (Ticker, Price) or (Price, Ticker) issues
        if isinstance(df.columns, pd.MultiIndex):
            # If 'Close' is a level, extract it
            if 'Close' in df.columns.get_level_values(0):
                 df = df['Close']
            
        # Drop rows with all NaNs
        df = df.dropna(how='all')
        
        # Fill forward to handle different trading days validation
        df = df.ffill()
        
        # Ensure benchmark exists
        if self.benchmark not in df.columns:
            raise ValueError(f"Benchmark {self.benchmark} not found in fetched data.")
            
        self.data = df
        return df

    def calculate(self):
        """Calculates JdK RS-Ratio and RS-Momentum."""
        if self.data is None:
            self.fetch_data()
            
        df = self.data
        bench_series = df[self.benchmark]
        
        results = {}
        
        for ticker in self.tickers:
            if ticker not in df.columns:
                continue
                
            # 1. Relative Strength (RS)
            rs = 100 * (df[ticker] / bench_series)
            
            # 2. RS-Ratio (Normalized RS)
            # RRG standard calculation approximates:
            # RS-Ratio = 100 + ((RS - MA(RS)) / STD(RS))
            # Note: We use ddof=0 for population std dev as is common in TA, 
            # though sample (ddof=1) is also fine.
            
            rs_mean = rs.rolling(window=self.window).mean()
            rs_std = rs.rolling(window=self.window).std(ddof=0)
            
            # Avoid division by zero
            rs_std = rs_std.replace(0, np.nan)
            
            # JdK RS-Ratio
            # Multiplied by factor? usually it's just centered at 100.
            # Z-score is usually -3 to +3. To center at 100 and scale nicely:
            # Maybe 100 + (Z * 10)? 
            # Original papers say normalization. 
            # Let's stick to the basic Z + 100. 
            # However, typical RRG charts show range 96-104. 
            # If Z is 1, 100+1 = 101. This fits.
            jdk_rs_ratio = 100 + ((rs - rs_mean) / rs_std)
            
            # 3. RS-Momentum
            # Rate of Change of the RS-Ratio
            # Momentum is the velocity of the ratio
            
            # Calculate Rate of Change (1 period difference)
            roc = jdk_rs_ratio.diff()
            
            roc_mean = roc.rolling(window=self.window).mean()
            roc_std = roc.rolling(window=self.window).std(ddof=0)
            roc_std = roc_std.replace(0, np.nan)
            
            jdk_rs_momentum = 100 + ((roc - roc_mean) / roc_std)
            
            # Combine into a DataFrame for this ticker
            ticker_df = pd.DataFrame({
                'RS_Ratio': jdk_rs_ratio,
                'RS_Momentum': jdk_rs_momentum
            })
            
            results[ticker] = ticker_df
            
        self.rrg_history = results
        return results

    def get_latest_values(self):
        """Returns the latest Ratio/Momentum for scatter plot."""
        if not self.rrg_history:
            return {}
            
        latest = {}
        for ticker, df in self.rrg_history.items():
            if not df.empty:
                row = df.iloc[-1]
                latest[ticker] = {
                    'RS_Ratio': row['RS_Ratio'],
                    'RS_Momentum': row['RS_Momentum']
                }
        return latest
        
    def get_trails(self, length=10):
        """Returns the last N points for plotting trails."""
        if not self.rrg_history:
            return {}
            
        trails = {}
        for ticker, df in self.rrg_history.items():
            if not df.empty:
                # Get last 'length' rows
                trails[ticker] = df.tail(length)
        return trails
