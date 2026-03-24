import yfinance as yf
import pandas as pd
import numpy as np
import io

class PortfolioOptimizer:
    def __init__(self, tickers, start_date, end_date=None, risk_free_rate=0.10, price_data=None):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date if end_date else pd.Timestamp.now().strftime('%Y-%m-%d')
        self.risk_free_rate = risk_free_rate
        self.data = pd.DataFrame()
    
    def fetch_data(self):
        if self.price_data_input is not None:
            data = self.price_data_input
        else:
            data = yf.download(self.tickers, start=self.start_date, end=self.end_date)['Close']
        us_stocks = [t for t in self.tickers if not t.endswith('.SA') and not '.' in t] 
        us_stocks = [t for t in self.tickers if not t.endswith('.SA') and not 'BRL' in t and not '=' in t]
         
        print(f"Fetching data for {self.tickers}...")
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date)['Close']
        
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
        
        returns = self.data.pct_change().dropna()
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov() * 252
    
    def optimize(self, num_portfolios=5000):
        if self.data.empty:
            self.fetch_data()
            
        # Geração de pesos vetorizada (sem loop)
        np.random.seed(42)
        # Cria uma matriz (num_portfolios, n_tickers) de uma vez
        weights_matrix = np.random.random((num_portfolios, len(self.tickers)))
        weights_matrix = (weights_matrix.T / weights_matrix.sum(axis=1)).T
        
        # Cálculos de Retorno e Volatilidade usando Álgebra Linear
        # Retorno: Produto escalar entre matriz de pesos e vetor de retornos médios
        p_returns = np.dot(weights_matrix, mean_returns)
        
        p_volatility = np.sqrt(np.einsum('ij,jk,ik->i', weights_matrix, cov_matrix, weights_matrix))
        
        # Sharpe Ratio vetorizado
        p_sharpe = (p_returns - self.risk_free_rate) / p_volatility
        
        results = np.array([p_returns, p_volatility, p_sharpe])
        
        max_sharpe_idx = np.argmax(p_sharpe)
        min_vol_idx = np.argmin(p_volatility)
    
    # ... (restante da lógica de métricas de curva de capital)
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
        
        rets = results[0]
        vols = results[1]
        
        
        norm_ret = (rets - rets.min()) / (rets.max() - rets.min())
        norm_vol = (vols - vols.min()) / (vols.max() - vols.min())
        
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
