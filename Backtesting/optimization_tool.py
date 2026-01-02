import yfinance as yf
import pandas as pd
import numpy as np
import io

class PortfolioOptimizer:
    def __init__(self, tickers, start_date, end_date=None, risk_free_rate=0.10):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date if end_date else pd.Timestamp.now().strftime('%Y-%m-%d')
        self.risk_free_rate = risk_free_rate
        self.data = pd.DataFrame()
    
    def fetch_data(self):
        # Similar data fetching logic as Backtester but simpler (just Close prices)
        # Assuming US stocks don't have .SA, same logic
        us_stocks = [t for t in self.tickers if not t.endswith('.SA') and not '.' in t] # Simple heuristic
        # Actually in the backtester we checked if it didn't end with .SA. 
        # But 'USDBRL=X' has . in it.
        # Let's rely on standard yfinance, user usually provides proper tickers.
        # But to be safe and consistent with backtester:
        us_stocks = [t for t in self.tickers if not t.endswith('.SA') and not 'BRL' in t and not '=' in t]
         
        print(f"Fetching data for {self.tickers}...")
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date)['Close']
        
        # Currency conv if needed
        if us_stocks:
             currency_data = yf.download("USDBRL=X", start=self.start_date, end=self.end_date)['Close']
             if isinstance(currency_data, pd.DataFrame): currency_data = currency_data.iloc[:, 0]
             currency_data = currency_data.ffill().bfill()
             
             # Reindex
             currency_data = currency_data.reindex(data.index).ffill().bfill()
             
             for ticker in us_stocks:
                 if ticker in data.columns:
                     data[ticker] = data[ticker] * currency_data
                     
        self.data = data.ffill().bfill().dropna()
        
    def optimize(self, num_portfolios=5000):
        if self.data.empty:
            self.fetch_data()
            
        # Daily Returns
        returns = self.data.pct_change()
        mean_returns = returns.mean()
        
        # AnnualCov
        cov_matrix = returns.cov() * 252
        
        # Annual Returns
        annual_returns = mean_returns * 252
        
        results = np.zeros((3, num_portfolios))
        weights_record = []
        
        np.random.seed(42)
        
        for i in range(num_portfolios):
            weights = np.random.random(len(self.tickers))
            weights /= np.sum(weights)
            weights_record.append(weights)
            
            p_ret = np.sum(weights * annual_returns)
            p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            # Sharpe (assuming Risk Free Rate)
            p_sharpe = (p_ret - self.risk_free_rate) / p_vol
            
            results[0,i] = p_ret
            results[1,i] = p_vol
            results[2,i] = p_sharpe
            
        # Helper for metrics
        def calc_metrics(w):
            port_ret = returns.dot(w)
            # Wealth Index
            wealth_index = (1 + port_ret).cumprod()
            peak = wealth_index.cummax()
            dd = (wealth_index - peak) / peak
            max_dd = dd.min()
            
            # Re-normalize for chart (Start at 100)
            equity_curve = 100 * (1 + port_ret).cumprod()
            equity_curve.iloc[0] = 100 # Adjust start? No, cumprod starts after first return. 
            # Better: Insert 100 at start.
            
            return max_dd, equity_curve

        # Locate Max Sharpe and Min Vol
        max_sharpe_idx = np.argmax(results[2])
        min_vol_idx = np.argmin(results[1])
        
        # --- NEW: Optimal (Distance to Utopia) ---
        # Normalize returns and volatility to 0-1 scale for fair distance calc
        rets = results[0]
        vols = results[1]
        
        # Utopia point: Max Return, Min Volatility
        # We want to minimize distance to (1, 0) in normalized space
        # where 1 is best return, 0 is best volatility (lowest)
        
        norm_ret = (rets - rets.min()) / (rets.max() - rets.min())
        norm_vol = (vols - vols.min()) / (vols.max() - vols.min())
        
        # Utopia: Max Return (norm=1), Min Vol (norm=0)
        # Distance = sqrt( (nR - 1)^2 + (nV - 0)^2 )
        distances = np.sqrt( (norm_ret - 1)**2 + (norm_vol - 0)**2 )
        optimal_idx = np.argmin(distances)
        
        w_sharpe = weights_record[max_sharpe_idx]
        w_vol = weights_record[min_vol_idx]
        w_opt = weights_record[optimal_idx]
        
        dd_sharpe, curve_sharpe = calc_metrics(w_sharpe)
        dd_vol, curve_vol = calc_metrics(w_vol)
        dd_opt, curve_opt = calc_metrics(w_opt)
        
        max_sharpe_port = {
            'Return': results[0, max_sharpe_idx],
            'Volatility': results[1, max_sharpe_idx],
            'Sharpe': results[2, max_sharpe_idx],
            'MaxDrawdown': dd_sharpe,
            'Weights': dict(zip(self.tickers, w_sharpe)),
            'EquityCurve': curve_sharpe
        }
        
        min_vol_port = {
            'Return': results[0, min_vol_idx],
            'Volatility': results[1, min_vol_idx],
            'Sharpe': results[2, min_vol_idx],
            'MaxDrawdown': dd_vol,
            'Weights': dict(zip(self.tickers, w_vol)),
            'EquityCurve': curve_vol
        }
        
        optimal_port = {
            'Return': results[0, optimal_idx],
            'Volatility': results[1, optimal_idx],
            'Sharpe': results[2, optimal_idx],
            'MaxDrawdown': dd_opt,
            'Weights': dict(zip(self.tickers, w_opt)),
            'EquityCurve': curve_opt
        }
        
        return results, max_sharpe_port, min_vol_port, optimal_port
