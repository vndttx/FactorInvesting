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
    def __init__(self, tickers, initial_investment, monthly_investment, start_date, end_date=None, benchmark_rate=0.10, risk_free_allocation=0.0, injected_data=None):
        self.tickers = tickers
        self.initial_investment = initial_investment
        self.monthly_investment = monthly_investment
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.benchmark_rate = benchmark_rate
        self.risk_free_allocation = risk_free_allocation
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.benchmark_rate = benchmark_rate
        self.data = pd.DataFrame()
        self.dividends = pd.DataFrame()
        self.currency = pd.DataFrame()
        self.price_data = None
        self.div_data = None
        self.daily_dividends = {}
        self.daily_returns_reinvest = []
        self.daily_returns_no_reinvest = []
        self.injected_data = injected_data #
        self.price_data = None
        
    def fetch_data(self):
        print("Fetching data...")
        us_stocks = [t for t in self.tickers if not t.endswith('.SA')]
        if self.injected_data is not None:
            data = self.injected_data
        else:
            data = yf.download(self.tickers, start=self.start_date, end=self.end_date, actions=True)
        
        us_stocks = [t for t in self.tickers if not t.endswith('.SA')]
        
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date, actions=True)
        
        print("Fetching Ibovespa data...")
        try:
             ibov_data = yf.download("^BVSP", start=self.start_date, end=self.end_date)['Close']
             if isinstance(ibov_data, pd.DataFrame):
                 ibov_data = ibov_data.iloc[:, 0]
             self.ibov_series = ibov_data.ffill().bfill()
        except Exception as e:
             print(f"Could not fetch Ibovespa: {e}")
             self.ibov_series = None


        if len(self.tickers) > 1:
            self.price_data = data['Close'].ffill().bfill()
            self.div_data = data['Dividends'].fillna(0)
        else:
            self.price_data = pd.DataFrame(data['Close']).rename(columns={'Close': self.tickers[0]}).ffill().bfill()
            self.div_data = pd.DataFrame(data['Dividends']).rename(columns={'Dividends': self.tickers[0]})
            
        if us_stocks:
            print("Fetching currency data for US stocks...")
            currency_data = yf.download("USDBRL=X", start=self.start_date, end=self.end_date)['Close']
            
            if isinstance(currency_data, pd.DataFrame):
                currency_data = currency_data.iloc[:, 0]
                
            self.currency_rate = currency_data.ffill().bfill()
            
            self.currency_rate = self.currency_rate.reindex(self.price_data.index).ffill().bfill()
 
            # Convert US stocks to BRL
            for ticker in us_stocks:
                if ticker in self.price_data.columns:
                    # Ensure we are multiplying Series by Series
                    self.price_data[ticker] = self.price_data[ticker] * self.currency_rate
                    # Fix: Dividends also need conversion
                    if ticker in self.div_data.columns:
                        self.div_data[ticker] = self.div_data[ticker] * self.currency_rate
        
        # Drop rows with all NaNs (holidays etc)
        self.price_data = self.price_data.dropna(how='all')
        # Ensure Naive TZ
        if self.price_data.index.tz is not None:
             self.price_data.index = self.price_data.index.tz_localize(None)
             
        self.div_data = self.div_data.loc[self.price_data.index].fillna(0)
        
        # Align IBOV
        if self.ibov_series is not None:
            # Ensure Naive
             if self.ibov_series.index.tz is not None:
                  self.ibov_series.index = self.ibov_series.index.tz_localize(None)
             self.ibov_series = self.ibov_series.reindex(self.price_data.index).ffill()
        
        # Fetch Risk Free
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
        if self.price_data is None:
            self.fetch_data()

        print("Running vectorized backtest...")
        
        prices = self.price_data
        asset_returns = prices.pct_change().fillna(0)
        
        n_assets = len(self.tickers)
        weights = np.array([1.0 / n_assets] * n_assets)
        
        portfolio_daily_ret = (asset_returns * weights).sum(axis=1)
        
        contributions = pd.Series(0.0, index=prices.index)
        contributions.iloc[0] = self.initial_investment * (1 - self.risk_free_allocation)
        
        monthly_mask = contributions.index.to_period('M') != contributions.index.to_period('M').shift(1)
        contributions[monthly_mask & (contributions.index != contributions.index[0])] = \
            self.monthly_investment * (1 - self.risk_free_allocation)
        
        portfolio_values = np.zeros(len(prices))
        current_val = 0
        
        for i in range(len(prices)):
            current_val = current_val * (1 + portfolio_daily_ret.iloc[i]) + contributions.iloc[i]
            portfolio_values[i] = current_val

        rf_daily_rates = self.risk_free_daily_series.fillna(0)
        rf_contributions = pd.Series(0.0, index=prices.index)
        rf_contributions.iloc[0] = self.initial_investment * self.risk_free_allocation
        rf_contributions[monthly_mask & (rf_contributions.index != rf_contributions.index[0])] = \
            self.monthly_investment * self.risk_free_allocation
        
        rf_values = np.zeros(len(prices))
        curr_rf = 0
        for i in range(len(prices)):
            curr_rf = curr_rf * (1 + rf_daily_rates.iloc[i]) + rf_contributions.iloc[i]
            rf_values[i] = curr_rf

        self.results = pd.DataFrame({
            'With Reinvestment': portfolio_values + rf_values,
            'Invested Capital': (contributions + rf_contributions).cumsum(),
            'Risk Free': self.calculate_benchmark_rf()
        }, index=prices.index)
        
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
