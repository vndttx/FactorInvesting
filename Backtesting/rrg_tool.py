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
        
        df = yf.download(all_symbols, start=self.start_date, progress=False, auto_adjust=True)
        
        if isinstance(df.columns, pd.MultiIndex):
            if 'Close' in df.columns.get_level_values(0):
                 df = df['Close']
            
        df = df.dropna(how='all')
        
        df = df.ffill()
        
        if self.benchmark not in df.columns:
            raise ValueError(f"Benchmark {self.benchmark} not found in fetched data.")
            
        self.data = df
        return df

    def calculate_rrg_metrics(self, price_data, benchmark_data, window_ratio=14, window_mom=14):
        rs_series = price_data.div(benchmark_data, axis=0)
        std_rs = rs_series.rolling(window=window_ratio).std()
        rs_ratio = 100 + ((rs_series - ema_rs) / std_rs) * 1
        rs_mom = 100 + (rs_ratio.pct_change(periods=window_mom) * 100)
        return rs_ratio.ffill(), rs_mom.ffill()

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
            rs = 100 * (df[ticker] / bench_series)
            

            rs_mean = rs.rolling(window=self.window).mean()
            rs_std = rs.rolling(window=self.window).std(ddof=0)
            

            rs_std = rs_std.replace(0, np.nan)
            
            jdk_rs_ratio = 100 + ((rs - rs_mean) / rs_std)

            roc = jdk_rs_ratio.diff()
            
            roc_mean = roc.rolling(window=self.window).mean()
            roc_std = roc.rolling(window=self.window).std(ddof=0)
            roc_std = roc_std.replace(0, np.nan)
            
            jdk_rs_momentum = 100 + ((roc - roc_mean) / roc_std)

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
