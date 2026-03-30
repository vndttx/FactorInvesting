import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.ticker as mtick
import requests
import io
import scipy.stats as stats

class PortfolioBacktester:
    def __init__(self, tickers, initial_investment, monthly_investment, start_date, end_date, benchmark_rate=0.10, rf_allocation=0.0, injected_data=None):
        self.tickers = tickers
        self.initial_investment = initial_investment
        self.monthly_investment = monthly_investment
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.benchmark_rate = benchmark_rate
        self.rf_allocation = rf_allocation
        self.data = pd.DataFrame()
        self.dividends = pd.DataFrame()
        self.currency = pd.DataFrame()
        self.price_data = None
        self.div_data = None
        self.daily_dividends = {}
        self.daily_returns_reinvest = []
        self.daily_returns_no_reinvest = []
        self.injected_data = injected_data #
        
    def fetch_data(self):
        print(f"Fetching data for: {self.tickers}")
        
        if self.injected_data is not None and not self.injected_data.empty:
            data = self.injected_data
        else:
            data = yf.download(self.tickers, start=self.start_date, end=self.end_date, actions=True, group_by='column')

        if data is None or data.empty:
            raise ValueError(f"Falha Crítica: Tickers não encontrados ou sem dados no período. Verifique se esqueceu o '.SA'")
            
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        if len(self.tickers) > 1:
            self.price_data = data['Close'].ffill().bfill()
            self.div_data = data['Dividends'].fillna(0)
        else:
            ticker = self.tickers[0]
            self.price_data = pd.DataFrame(data['Close']).rename(columns={'Close': ticker}).ffill().bfill()
            self.div_data = pd.DataFrame(data['Dividends']).rename(columns={'Dividends': ticker}).fillna(0)

        us_stocks = [t for t in self.tickers if not t.endswith('.SA')]
        if us_stocks:
            print("Fetching currency data for US stocks...")
            currency_df = yf.download("USDBRL=X", start=self.start_date, end=self.end_date)['Close']
            
            if isinstance(currency_df, pd.DataFrame):
                currency_df = currency_df.iloc[:, 0]
            if currency_df.index.tz is not None:
                currency_df.index = currency_df.index.tz_localize(None)
                
            self.currency_rate = currency_df.reindex(self.price_data.index).ffill().bfill()

            for ticker in us_stocks:
                if ticker in self.price_data.columns:
                    self.price_data[ticker] = self.price_data[ticker] * self.currency_rate
                    if ticker in self.div_data.columns:
                        self.div_data[ticker] = self.div_data[ticker] * self.currency_rate

        # 5. Benchmark Ibovespa
        print("Fetching Ibovespa data...")
        try:
            ibov_df = yf.download("^BVSP", start=self.start_date, end=self.end_date)['Close']
            if isinstance(ibov_df, pd.DataFrame):
                ibov_df = ibov_df.iloc[:, 0]
            if ibov_df.index.tz is not None:
                ibov_df.index = ibov_df.index.tz_localize(None)
            self.ibov_series = ibov_df.reindex(self.price_data.index).ffill().bfill()
        except Exception as e:
            print(f"Could not fetch Ibovespa: {e}")
            self.ibov_series = None

        # 6. Alinhamento final e Risk Free
        self.price_data = self.price_data.dropna(how='all')
        self.div_data = self.div_data.loc[self.price_data.index].fillna(0)
        self.fetch_risk_free_data()

    def fetch_risk_free_data(self):
        print("Fetching historical Risk-Free Rate (Selic) from Ipeadata...")
        
        url = "http://www.ipeadata.gov.br/api/odata4/Metadados('GM366_TJOVER366')/Valores"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data_json = response.json()
            
            if 'value' in data_json:
                df = pd.DataFrame(data_json['value'])
                # Columns: VALDATA, VALVALOR (Annualized %)
                # Parse, convert to naive, and Normalize (set time to 00:00:00) 
                df['Date'] = pd.to_datetime(df['VALDATA'], utc=True).dt.tz_convert(None).dt.normalize()
                df.set_index('Date', inplace=True)
                df = df.sort_index()
                
                # Filter for our range
                start_dt = pd.to_datetime(self.start_date)
                end_dt = pd.to_datetime(self.end_date)
                
                df = df.loc[start_dt:end_dt]
                
                # Reindex to match price_data (trading days)
                aligned_selic = df['VALVALOR'].reindex(self.price_data.index).ffill().fillna(0)
                
                self.risk_free_daily_series = (1 + aligned_selic / 100) ** (1/252) - 1
                
                print("Risk-Free data fetched and aligned.")
                
        except Exception as e:
            print(f"Failed to fetch Risk Free Data: {e}")
            print("Falling back to fixed benchmark rate.")
            daily_fixed = (1 + self.benchmark_rate) ** (1/252) - 1
            self.risk_free_daily_series = pd.Series(daily_fixed, index=self.price_data.index)
    
    def calculate_benchmark_rf(self):
        if self.risk_free_daily_series is None:
            # Fallback caso a série da Selic falhe
            days = len(self.price_data)
            daily_rate = (1 + self.benchmark_rate) ** (1/252) - 1
            return self.initial_investment * (np.power(1 + daily_rate, np.arange(days)))
        
        # Cálculo usando a série real da Selic/CDI
        # (1 + taxa_diaria).cumprod() gera o fator acumulado
        rf_factor = (1 + self.risk_free_daily_series.fillna(0)).cumprod()
        return self.initial_investment * rf_factor
            
    def run(self):
        try:
            self.fetch_data()
            prices = self.price_data
            n_assets = len(self.tickers)
            weights = np.array([1.0 / n_assets] * n_assets)
            
            months = prices.index.month
            monthly_mask = np.zeros(len(prices), dtype=bool)
            for i in range(1, len(prices)):
                if months[i] != months[i-1]:
                    monthly_mask[i] = True
            
            shares_owned = pd.DataFrame(0.0, index=prices.index, columns=self.tickers)
            rf_values = np.zeros(len(prices))
            portfolio_values = np.zeros(len(prices))
            
            rf_daily = self.risk_free_daily_series.reindex(prices.index).fillna(0)
            curr_rf_balance = 0
            
            alloc_rf = self.rf_allocation
            if alloc_rf > 1:
                alloc_rf = alloc_rf / 100.0

            for i in range(len(prices)):
                is_start = (i == 0)
                is_monthly = monthly_mask[i]
                
                if is_start or is_monthly:
                    total_contribution = self.initial_investment if is_start else self.monthly_investment
                    
                    risk_contribution = total_contribution * (1 - alloc_rf)
                    rf_contribution = total_contribution * alloc_rf
                    
                    curr_rf_balance += rf_contribution
                    
                    if risk_contribution > 0:
                        for idx, ticker in enumerate(self.tickers):
                            p_today = prices[ticker].iloc[i]
                            if p_today > 0:
                                added = (risk_contribution * weights[idx]) / p_today
                                shares_owned.loc[prices.index[i:], ticker] += added

                curr_rf_balance = curr_rf_balance * (1 + rf_daily.iloc[i])
                rf_values[i] = curr_rf_balance
                portfolio_values[i] = (shares_owned.iloc[i] * prices.iloc[i]).sum() + rf_values[i]

            portfolio_series = pd.Series(portfolio_values, index=prices.index)
            
            total_invested_series = pd.Series(0.0, index=prices.index)
            total_invested_series.iloc[0] = self.initial_investment
            for i in range(1, len(prices)):
                total_invested_series.iloc[i] = total_invested_series.iloc[i-1]
                if monthly_mask[i]:
                    total_invested_series.iloc[i] += self.monthly_investment

            rf_bench_vals = np.zeros(len(prices))
            curr_bench_rf = 0
            for i in range(len(prices)):
                contrib = self.initial_investment if i == 0 else (self.monthly_investment if monthly_mask[i] else 0)
                curr_bench_rf = curr_bench_rf * (1 + rf_daily.iloc[i]) + contrib
                rf_bench_vals[i] = curr_bench_rf
            rf_bench_series = pd.Series(rf_bench_vals, index=prices.index)

            ibov_bench_series = None
            if hasattr(self, 'ibov_series') and self.ibov_series is not None:
                ibov_ret = self.ibov_series.pct_change().fillna(0)
                ibov_vals = np.zeros(len(prices))
                curr_ib = 0
                for i in range(len(prices)):
                    contrib = self.initial_investment if i == 0 else (self.monthly_investment if monthly_mask[i] else 0)
                    curr_ib = curr_ib * (1 + ibov_ret.iloc[i]) + contrib
                    ibov_vals[i] = curr_ib
                ibov_bench_series = pd.Series(ibov_vals, index=prices.index)

            real_dividends = (self.div_data * shares_owned).sum(axis=1)
            df_divs = real_dividends.to_frame(name='divs')
            df_divs['year'], df_divs['month'] = df_divs.index.year, df_divs.index.month
            div_matrix = df_divs.groupby(['year', 'month'])['divs'].sum().unstack(fill_value=0)

            final_val = portfolio_series.iloc[-1]
            total_cap = total_invested_series.iloc[-1]
            
            return {
                'portfolio_pct': (portfolio_series / total_invested_series - 1) * 100,
                'rf_pct': (rf_bench_series / total_invested_series - 1) * 100,
                'ibov_pct': (ibov_bench_series / total_invested_series - 1) * 100 if ibov_bench_series is not None else None,
                'div_matrix': div_matrix,
                'stats': {
                    'Total Return': ((final_val / total_cap) - 1) * 100,
                    'CAGR': (((final_val / total_cap) ** (365.0 / (prices.index[-1] - prices.index[0]).days)) - 1) * 100,
                    'Sharpe Ratio': (((final_val / total_cap) - 1) / (portfolio_series.pct_change().std() * np.sqrt(252))) if portfolio_series.pct_change().std() > 0 else 0,
                    'Max Drawdown': ((portfolio_series / portfolio_series.cummax()) - 1).min() * 100,
                    'Volatility': portfolio_series.pct_change().std() * np.sqrt(252) * 100
                }
            }
        except Exception as e:
            print(f"Erro: {e}")
            return None
        
    def display_monthly_income(self):
        if not self.daily_dividends:
            print("No dividends received.")
            return

        # Convert to DataFrame
        df_divs = pd.DataFrame.from_dict(self.daily_dividends, orient='index', columns=['Dividend'])
        df_divs.index = pd.to_datetime(df_divs.index)
        
        # Group by Year and Month
        df_divs['Year'] = df_divs.index.year
        df_divs['Month'] = df_divs.index.month
        
        monthly_pivot = df_divs.pivot_table(index='Year', columns='Month', values='Dividend', aggfunc='sum').fillna(0)
        
        # Add Total Column
        monthly_pivot['Total'] = monthly_pivot.sum(axis=1)
        
        # Format columns maps 1..12 to Jan..Dec
        month_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 
                     7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        monthly_pivot = monthly_pivot.rename(columns=month_map)
        
        print("\n=== Monthly Dividend Income (BRL) ===")
        # Print formatted
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        # Format float
        print(monthly_pivot.applymap(lambda x: f"{x:,.2f}"))
        
    def display_metrics(self):
        m_reinvest = self.calculate_metrics(self.daily_returns_reinvest, self.risk_free_daily_series.values)
        m_no_reinvest = self.calculate_metrics(self.daily_returns_no_reinvest, self.risk_free_daily_series.values)
        
        print("\n=== Performance Metrics ===")

        print(f"{'Metric':<20} | {'With Reinvest':<15} | {'No Reinvest':<15}")
        print("-" * 56)
        
        for k in m_reinvest.keys():
            val_r = m_reinvest[k]
            val_nr = m_no_reinvest[k]
            
            # Format
            if k in ["Total Return", "CAGR", "Volatility", "Max Drawdown"]:
                fmt_r = f"{val_r*100:.2f}%"
                fmt_nr = f"{val_nr*100:.2f}%"
            else:
                fmt_r = f"{val_r:.2f}"
                fmt_nr = f"{val_nr:.2f}"
                
            print(f"{k:<20} | {fmt_r:<15} | {fmt_nr:<15}")
            
    def plot(self):
        plt.figure(figsize=(12, 6))
        plt.plot(self.results.index, self.results['With Reinvestment'], label='With Dividends Reinvested')
        plt.plot(self.results.index, self.results['Without Reinvestment'], label='Without Reinvestment (Divs kept in Cash)')
        plt.plot(self.results.index, self.results['Risk Free'], label='Risk Free (CDI)', linestyle='--')

        
        plt.title('Portfolio Backtest Performance (BRL)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value (BRL)')
        
        # Format Y-axis as Currency BRL
        def currency(x, pos):
            return f'R$ {x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            
        plt.gca().yaxis.set_major_formatter(mtick.FuncFormatter(currency))
        
        plt.legend()
        plt.grid(True)
        plt.show()

    def calculate_metrics(self, returns_series, risk_free_series=None):

        if not returns_series:
            return {}
            
        returns = pd.Series(returns_series)
        
        if risk_free_series is not None:
            rf = pd.Series(risk_free_series)
            if len(rf) != len(returns):
                rf_val = rf.mean()
                excess_returns = returns - rf_val
            else:
                excess_returns = returns - rf
        else:
             rf_fixed = (1 + self.benchmark_rate) ** (1/252) - 1
             excess_returns = returns - rf_fixed

        
        total_return = (1 + returns).prod() - 1
        
        n_days = len(returns)
        if n_days > 0:
            cagr = (1 + total_return) ** (252 / n_days) - 1
        else:
            cagr = 0.0
            
        volatility = returns.std() * (252 ** 0.5)
        
        sharpe = (excess_returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() > 0 else 0

        wealth_index = (1 + returns).cumprod()
        peak = wealth_index.cummax()
        drawdown = (wealth_index - peak) / peak
        max_drawdown = drawdown.min()
        
        return {
            "Total Return": total_return,
            "CAGR": cagr,
            "Volatility": volatility,
            "Max Drawdown": max_drawdown
        }

    def calculate_beta(self, portfolio_returns, benchmark_name='^BVSP'):

        if self.ibov_series is None:
             return 0.0
             
        bench_ret = self.ibov_series.pct_change().dropna()
        port_ret = pd.Series(portfolio_returns, index=self.price_data.index).dropna()
        
        df_join = pd.concat([port_ret, bench_ret], axis=1, join='inner').dropna()
        
        if df_join.empty:
            return 0.0
            
        rp = df_join.iloc[:, 0]
        rb = df_join.iloc[:, 1]
        
        covariance = np.cov(rp, rb)[0, 1]
        variance = np.var(rb)
        
        if variance == 0:
            return 0.0
            
        return covariance / variance

if __name__ == "__main__":
    tickers = ['BBAS3.SA', 'ITUB4.SA','CMIG4.SA', 'CPLE6.SA', 'CSMG3.SA', 'VIVT3.SA', 'TIMS3.SA', 'BBSE3.SA', 'KLBN11.SA']
    initial = 800
    monthly = 600
    start = '2015-01-01'
    end = datetime.now().strftime('%Y-%m-%d')
    
    bt = PortfolioBacktester(tickers, initial, monthly, start)
    bt.run()
    bt.display_monthly_income()
    bt.display_metrics()
    bt.plot()
    
    print("\nFinal Values (BRL):")
    final_values = bt.results.iloc[-1]
    for key, value in final_values.items():
        formatted_value = f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        print(f"{key:<25}: {formatted_value}")
