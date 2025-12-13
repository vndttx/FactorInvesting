import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.ticker as mtick
import requests
import io

class PortfolioBacktester:
    def __init__(self, tickers, initial_investment, monthly_investment, start_date, end_date=None, benchmark_rate=0.10, weights=None):
        self.tickers = tickers
        self.initial_investment = initial_investment
        self.monthly_investment = monthly_investment
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.benchmark_rate = benchmark_rate
        
        if weights is None:
            n = len(tickers)
            self.weights = {t: 1.0/n for t in tickers}
        else:
            total_w = sum(weights.values())
            self.weights = {t: weights.get(t, 0)/total_w for t in tickers}
            
        self.data = pd.DataFrame()
        self.dividends = pd.DataFrame()
        self.currency = pd.DataFrame()
        self.price_data = None
        self.div_data = None
        self.daily_dividends = {}
        self.risk_free_daily_series = None
        self.daily_returns_reinvest = []
        self.daily_returns_no_reinvest = []

    def fetch_data(self):
        print("Fetching data...")
        us_stocks = [t for t in self.tickers if not t.endswith('.SA')]
        
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date, actions=True)
        
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

            for ticker in us_stocks:
                if ticker in self.price_data.columns:
                    self.price_data[ticker] = self.price_data[ticker] * self.currency_rate
                    if ticker in self.div_data.columns:
                        self.div_data[ticker] = self.div_data[ticker] * self.currency_rate
        
        self.price_data = self.price_data.dropna(how='all')
        if self.price_data.index.tz is not None:
             self.price_data.index = self.price_data.index.tz_localize(None)
             
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
                df['Date'] = pd.to_datetime(df['VALDATA'], utc=True).dt.tz_convert(None).dt.normalize()
                df.set_index('Date', inplace=True)
                df = df.sort_index()
                
                start_dt = pd.to_datetime(self.start_date)
                end_dt = pd.to_datetime(self.end_date)
                
                df = df.loc[start_dt:end_dt]
                
                aligned_selic = df['VALVALOR'].reindex(self.price_data.index).ffill().fillna(0)
                
                self.risk_free_daily_series = (1 + aligned_selic / 100) ** (1/252) - 1
                
                print("Risk-Free data fetched and aligned.")
                
        except Exception as e:
            print(f"Failed to fetch Risk Free Data: {e}")
            print("Falling back to fixed benchmark rate.")
            daily_fixed = (1 + self.benchmark_rate) ** (1/252) - 1
            self.risk_free_daily_series = pd.Series(daily_fixed, index=self.price_data.index)
        
    def run(self):
        if self.price_data is None:
            self.fetch_data()
            
        print("Running backtest...")
        
        dates = self.price_data.index
        n_days = len(dates)
        
        shares_reinvest = {t: 0.0 for t in self.tickers}
        cash_reinvest = 0.0
        portfolio_reinvest = []
        invested_capital = 0.0
        
        shares_no_reinvest = {t: 0.0 for t in self.tickers}
        cash_wallet_no_reinvest = 0.0
        cash_residual_no_reinvest = 0.0
        portfolio_no_reinvest = []
        
        last_month = dates[0].month
        
        cash_reinvest += self.initial_investment
        cash_residual_no_reinvest += self.initial_investment
        invested_capital += self.initial_investment
        
        for t in self.tickers:
            price = self.price_data.iloc[0][t]
            if not pd.isna(price) and price > 0:
                alloc = self.initial_investment * self.weights[t]
                bought = alloc / price

                shares_reinvest[t] += bought
                cash_reinvest -= alloc

                shares_no_reinvest[t] += bought
                cash_residual_no_reinvest -= alloc

        for i in range(n_days):
            date = dates[i]
            prices = self.price_data.iloc[i]
            divs = self.div_data.iloc[i]
            
            current_flow = 0.0
            
            if i > 0 and date.month != last_month:
                current_flow = self.monthly_investment
                invested_capital += self.monthly_investment
                
                cash_reinvest += self.monthly_investment
                pool_to_invest = cash_reinvest
                
                to_invest_nr = self.monthly_investment
                
                for t in self.tickers:
                    price = prices[t]
                    if not pd.isna(price) and price > 0:
                        alloc_r = pool_to_invest * self.weights[t]
                        bought_r = alloc_r / price
                        shares_reinvest[t] += bought_r
                        
                        alloc_nr = to_invest_nr * self.weights[t]
                        bought_nr = alloc_nr / price

                        shares_no_reinvest[t] += bought_nr
                
                cash_reinvest = 0.0
                
                last_month = date.month
            
            for t in self.tickers:
                d_per_share = divs[t]
                if d_per_share > 0:
                    payout_r = shares_reinvest[t] * d_per_share
                    
                    if date not in self.daily_dividends:
                        self.daily_dividends[date] = 0.0
                    self.daily_dividends[date] += payout_r

                    cash_reinvest += payout_r
                    
                    payout_nr = shares_no_reinvest[t] * d_per_share
                    cash_wallet_no_reinvest += payout_nr
            
            val_reinvest = 0.0
            val_no_reinvest = 0.0
            
            for t in self.tickers:
                price = prices[t]
                if pd.isna(price): 
                    price = 0.0
                
                val_reinvest += shares_reinvest[t] * price
                val_no_reinvest += shares_no_reinvest[t] * price
            
            val_reinvest += cash_reinvest

            val_no_reinvest += cash_wallet_no_reinvest
            
            portfolio_reinvest.append(val_reinvest)
            portfolio_no_reinvest.append(val_no_reinvest)
            
            prev_val_r = portfolio_reinvest[i-1] if i > 0 else self.initial_investment
            prev_val_nr = portfolio_no_reinvest[i-1] if i > 0 else self.initial_investment
            
            denom_r = prev_val_r + current_flow
            denom_nr = prev_val_nr + current_flow
            
            ret_r = (val_reinvest / denom_r) - 1 if denom_r > 0 else 0.0
            ret_nr = (val_no_reinvest / denom_nr) - 1 if denom_nr > 0 else 0.0
            
            self.daily_returns_reinvest.append(ret_r)
            self.daily_returns_no_reinvest.append(ret_nr)

        self.results = pd.DataFrame({
            'With Reinvestment': portfolio_reinvest,
            'Without Reinvestment': portfolio_no_reinvest
        }, index=dates)
        
        rf_balance = 0.0
        rf_curve = []
        
        last_m = dates[0].month
        rf_added_initial = False
        
        rf_balance = self.initial_investment
        
        if self.risk_free_daily_series is None:
             daily_fixed = (1 + self.benchmark_rate) ** (1/252) - 1
             r_series = pd.Series(daily_fixed, index=dates)
        else:
             r_series = self.risk_free_daily_series
        
        for i in range(n_days):
            date = dates[i]
            if i > 0 and date.month != last_m:
                 rf_balance += self.monthly_investment
                 last_m = date.month
            
            if i > 0:
                r_day = r_series.get(date, 0.0)
                rf_balance *= (1 + r_day)
            
            rf_curve.append(rf_balance)
            
        self.results['Risk Free'] = rf_curve
        
        inv_cap_series = []
        curr_cap = self.initial_investment
        last_m = dates[0].month
        
        for i in range(n_days):
            date = dates[i]
            if i > 0 and date.month != last_m:
                curr_cap += self.monthly_investment
                last_m = date.month
            inv_cap_series.append(curr_cap)
            
        self.results['Invested Capital'] = inv_cap_series
        
    def display_monthly_income(self):
        if not self.daily_dividends:
            print("No dividends received.")
            return

        df_divs = pd.DataFrame.from_dict(self.daily_dividends, orient='index', columns=['Dividend'])
        df_divs.index = pd.to_datetime(df_divs.index)
        
        df_divs['Year'] = df_divs.index.year
        df_divs['Month'] = df_divs.index.month
        
        monthly_pivot = df_divs.pivot_table(index='Year', columns='Month', values='Dividend', aggfunc='sum').fillna(0)
        
        monthly_pivot['Total'] = monthly_pivot.sum(axis=1)
        
        month_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 
                     7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        monthly_pivot = monthly_pivot.rename(columns=month_map)
        
        print("\n=== Monthly Dividend Income (BRL) ===")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
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
            "Sharpe Ratio": sharpe,
            "Max Drawdown": max_drawdown
        }

if __name__ == "__main__":
    tickers = ['BBAS3.SA', 'ITUB4.SA','CMIG4.SA', 'TAEE11.SA', 'CSMG3.SA', 'VIVT3.SA', 'BBSE3.SA']
    initial = 1000
    monthly = 500
    start = '2015-01-01'
    
    weights = {
        'BBAS3.SA': 0.15, 
        'ITUB4.SA': 0.15, 
        'CMIG4.SA': 0.15, 
        'TAEE11.SA': 0.15, 
        'CSMG3.SA': 0.15,
        'VIVT3.SA': 0.10, 
        'BBSE3.SA': 0.15
    }
    
    print("Running with Custom Weights...")
    bt = PortfolioBacktester(tickers, initial, monthly, start, weights=weights) 
    
    bt.run()
    bt.display_monthly_income()
    bt.display_metrics()
    bt.plot()
    
    print("\nFinal Values (BRL):")
    final_values = bt.results.iloc[-1]
    for key, value in final_values.items():
        formatted_value = f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        print(f"{key:<25}: {formatted_value}")
