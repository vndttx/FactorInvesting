import yfinance as yf
import pandas as pd
import numpy as np

class PortfolioOptimizer:
    def __init__(self, tickers, start_date, end_date=None, risk_free_rate=0.10, price_data=None):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date if end_date else pd.Timestamp.now().strftime('%Y-%m-%d')
        self.risk_free_rate = risk_free_rate
        self.price_data_input = price_data
        self.data = pd.DataFrame()
        self.returns = pd.DataFrame()
        self.mean_returns = None
        self.cov_matrix = None

    def fetch_data(self):
        if self.price_data_input is not None:
            if isinstance(self.price_data_input, pd.DataFrame) and 'Close' in self.price_data_input.columns:
                data = self.price_data_input['Close']
            else:
                data = self.price_data_input
        else:
            data = yf.download(self.tickers, start=self.start_date, end=self.end_date)['Close']
        
        if isinstance(data, pd.Series):
            data = data.to_frame(name=self.tickers[0])

        us_stocks = [t for t in self.tickers if not t.endswith('.SA') and not 'BRL' in t and not '=' in t]
        
        if us_stocks:
            currency_data = yf.download("USDBRL=X", start=self.start_date, end=self.end_date)['Close']
            if isinstance(currency_data, pd.DataFrame): 
                currency_data = currency_data.iloc[:, 0]
            currency_data = currency_data.reindex(data.index).ffill().bfill()
            
            for ticker in us_stocks:
                if ticker in data.columns:
                    data[ticker] = data[ticker] * currency_data
                    
        self.data = data.ffill().bfill().dropna()
        self.returns = self.data.pct_change().dropna()
        self.mean_returns = self.returns.mean() * 252
        self.cov_matrix = self.returns.cov() * 252

    def optimize(self, num_portfolios=5000):
        if self.data.empty:
            self.fetch_data()
            
        np.random.seed(42)
        num_assets = len(self.tickers)
        weights_record = np.random.random((num_portfolios, num_assets))
        weights_record = (weights_record.T / weights_record.sum(axis=1)).T

        p_returns = np.dot(weights_record, self.mean_returns)
        p_volatility = np.sqrt(np.einsum('ij,jk,ik->i', weights_record, self.cov_matrix, weights_record))
        p_sharpe = (p_returns - self.risk_free_rate) / p_volatility
        
        results = np.array([p_returns, p_volatility, p_sharpe])
        
        def calc_metrics(w):
            port_ret = self.returns.dot(w)
            wealth_index = (1 + port_ret).cumprod()
            peak = wealth_index.cummax()
            max_dd = ((wealth_index - peak) / peak).min()
            equity_curve = 100 * wealth_index
            return max_dd, equity_curve

        max_sharpe_idx = np.argmax(results[2])
        min_vol_idx = np.argmin(results[1])
        
        rets, vols = results[0], results[1]
        norm_ret = (rets - rets.min()) / (rets.max() - rets.min())
        norm_vol = (vols - vols.min()) / (vols.max() - vols.min())
        distances = np.sqrt((norm_ret - 1)**2 + (norm_vol - 0)**2)
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