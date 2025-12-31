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
    def __init__(self, tickers, initial_investment, monthly_investment, start_date, end_date=None, benchmark_rate=0.10, risk_free_allocation=0.0):
        """
        initial_investment: Amount in BRL
        monthly_investment: Amount in BRL
        benchmark_rate: Annual risk-free rate (decimal, e.g., 0.10 for 10%)
        risk_free_allocation: Fraction of investment to go to Risk Free Asset (0.0 to 1.0)
        """
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
        self.daily_dividends = {} # Date -> Amount
        self.risk_free_daily_series = None # Date -> Daily Rate (decimal)
        self.daily_returns_reinvest = []
        self.daily_returns_no_reinvest = []



        
    def fetch_data(self):
        print("Fetching data...")
        # Add currency if there are US stocks (assuming US stocks don't have .SA)
        us_stocks = [t for t in self.tickers if not t.endswith('.SA')]
        
        # Download Stock Data
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date, actions=True)
        
        # Download Benchmark Data (IBOV)
        print("Fetching Ibovespa data...")
        try:
             ibov_data = yf.download("^BVSP", start=self.start_date, end=self.end_date)['Close']
             if isinstance(ibov_data, pd.DataFrame):
                 ibov_data = ibov_data.iloc[:, 0]
             self.ibov_series = ibov_data.ffill().bfill()
        except Exception as e:
             print(f"Could not fetch Ibovespa: {e}")
             self.ibov_series = None

        
        # Handle Multi-Index (Close, Dividends)
        # Handle Multi-Index (Close, Dividends)
        if len(self.tickers) > 1:
            self.price_data = data['Close'].ffill().bfill()
            self.div_data = data['Dividends'].fillna(0)
        else:
            # If single ticker, structure is different
            self.price_data = pd.DataFrame(data['Close']).rename(columns={'Close': self.tickers[0]}).ffill().bfill()
            self.div_data = pd.DataFrame(data['Dividends']).rename(columns={'Dividends': self.tickers[0]})
            
        # Download Currency Data for US Stocks
        if us_stocks:
            print("Fetching currency data for US stocks...")
            # We need BRL to convert USD assets to BRL
            # USDBRL=X is the ticker for how many BRL one USD buys. 
            currency_data = yf.download("USDBRL=X", start=self.start_date, end=self.end_date)['Close']
            
            # Ensure it is a Series
            if isinstance(currency_data, pd.DataFrame):
                currency_data = currency_data.iloc[:, 0]
                
            self.currency_rate = currency_data.ffill().bfill()
            
            # Align Currency Date with Stock Date
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
                
                # Convert Annualized % to Daily Decimal
                # R_daily = (1 + R_annual/100)^(1/252) - 1
                self.risk_free_daily_series = (1 + aligned_selic / 100) ** (1/252) - 1
                
                print("Risk-Free data fetched and aligned.")
                
        except Exception as e:
            print(f"Failed to fetch Risk Free Data: {e}")
            print("Falling back to fixed benchmark rate.")
            # Fallback
            daily_fixed = (1 + self.benchmark_rate) ** (1/252) - 1
            self.risk_free_daily_series = pd.Series(daily_fixed, index=self.price_data.index)
        
    def run(self):
        if self.price_data is None:
            self.fetch_data()
            
        print("Running backtest...")
        
        # Simulation Arrays
        dates = self.price_data.index
        n_days = len(dates)
        
        # 1. Strategy: Reinvest Dividends
        shares_reinvest = {t: 0.0 for t in self.tickers}
        cash_reinvest = 0.0 # Residual cash
        portfolio_reinvest = []
        invested_capital = 0.0
        
        # Risk Free Asset Tracker (Same for both strategies as we just accumulate allocation)
        rf_asset_value = 0.0 
        
        # Benchmark Tracker (Ibovespa)
        ibov_shares = 0.0
        ibov_curve = []
        
        # 2. Strategy: No Reinvest (Take Dividends as Cash)
        shares_no_reinvest = {t: 0.0 for t in self.tickers}
        cash_wallet_no_reinvest = 0.0 # Accumulated dividends
        cash_residual_no_reinvest = 0.0 # Small amounts from buying
        portfolio_no_reinvest = [] # Total Wealth (Shares + Cash Wallet)
        
        # Track monthly contributions
        last_month = dates[0].month
        
        # Initial Deposit
        # Split Allocation
        rf_initial = self.initial_investment * self.risk_free_allocation
        stock_initial = self.initial_investment * (1 - self.risk_free_allocation)
        
        rf_asset_value += rf_initial
        
        cash_reinvest += stock_initial
        cash_residual_no_reinvest += stock_initial
        invested_capital += self.initial_investment
        
        # Initialize Ibovespa Benchmark (Assuming 100% allocation to IBOV)
        if hasattr(self, 'ibov_series') and self.ibov_series is not None:
             ibov_start_price = self.ibov_series.iloc[0]
             if ibov_start_price > 0:
                  ibov_shares = self.initial_investment / ibov_start_price
        
        # Distribute initial cash equally among stocks
        weight = 1.0 / len(self.tickers)
        
        for t in self.tickers:
            price = self.price_data.iloc[0][t]
            if not pd.isna(price) and price > 0:
                # Buy for Reinvest Strat
                alloc = stock_initial * weight
                bought = alloc / price
                shares_reinvest[t] += bought
                cash_reinvest -= alloc 
                
                # Buy for No Reinvest Strat
                shares_no_reinvest[t] += bought
                cash_residual_no_reinvest -= alloc

        # Fix floating point drift or assume strictly 0 if we assume fractional shares allowed
        # To be precise let's just assume we track Value directly: Value = Shares * Price + Cash
        # But for Dividends logic we need Shares count.
        
        if self.risk_free_daily_series is None:
             # Fallback just in case
             daily_fixed_rate = (1 + self.benchmark_rate) ** (1/252) - 1
             rf_series_fallback = pd.Series(daily_fixed_rate, index=dates)
        
        for i in range(n_days):
            date = dates[i]
            prices = self.price_data.iloc[i]
            divs = self.div_data.iloc[i]
            
            # Grow Risk Free Asset
            if i > 0:
                if self.risk_free_daily_series is not None:
                     r_day = self.risk_free_daily_series.get(date, 0.0)
                else:
                     r_day = rf_series_fallback.get(date, 0.0)
                rf_asset_value *= (1 + r_day)
            
            # Flow Tracker
            current_flow = 0.0
            
            # Check for Monthly Contribution
            # Simple logic: if month changed, add money
            # (Skip first day as it was initial)
            if i > 0 and date.month != last_month:
                current_flow = self.monthly_investment
                invested_capital += self.monthly_investment
                
                # Split Monthly Allocation
                rf_monthly = self.monthly_investment * self.risk_free_allocation
                stock_monthly = self.monthly_investment * (1 - self.risk_free_allocation)
                
                # Add to RF Asset
                rf_asset_value += rf_monthly
                
                # REINVEST STRATEGY: Pool + Monthly Stock Part
                cash_reinvest += stock_monthly
                pool_to_invest = cash_reinvest
                
                # NO REINVEST STRATEGY: Just Monthly Stock Part
                to_invest_nr = stock_monthly

                
                # Buy Stocks (Equal Weight)
                for t in self.tickers:
                    price = prices[t]
                    if not pd.isna(price) and price > 0:
                        # Reinvest Strat
                        alloc_r = pool_to_invest * weight
                        bought_r = alloc_r / price
                        shares_reinvest[t] += bought_r
                        
                        # No Reinvest Strat
                        alloc_nr = to_invest_nr * weight
                        bought_nr = alloc_nr / price
                        shares_no_reinvest[t] += bought_nr
                
                # Buy Ibovespa (Benchmark)
                if hasattr(self, 'ibov_series') and self.ibov_series is not None:
                     ibov_price = self.ibov_series.iloc[i]
                     if ibov_price > 0:
                          # Benchmark gets full monthly investment (Passive 100% Stock Benchmark)
                          ibov_shares += self.monthly_investment / ibov_price
                
                # Reset cash pool
                cash_reinvest = 0.0
                
                last_month = date.month
            
            # Handle Dividends
            # Reinvest Strat: Divs -> Buy Shares
            for t in self.tickers:
                d_per_share = divs[t]
                if d_per_share > 0:
                    # REINVEST
                    # Total Div Received
                    payout_r = shares_reinvest[t] * d_per_share
                    
                    # Track for Table
                    if date not in self.daily_dividends:
                        self.daily_dividends[date] = 0.0
                    self.daily_dividends[date] += payout_r

                    # POOL DIVIDENDS (Do not buy immediately)
                    cash_reinvest += payout_r

                    
                    # NO REINVEST
                    payout_nr = shares_no_reinvest[t] * d_per_share
                    cash_wallet_no_reinvest += payout_nr
            
            # Calculate Daily Total Value
            val_reinvest = 0.0
            val_no_reinvest = 0.0
            
            for t in self.tickers:
                price = prices[t]
                if pd.isna(price): 
                    # If price is missing (holiday?), use previous? ffill handled it.
                    # If still NaN (start of history for some stocks), assume 0 val?
                    price = 0.0
                
                val_reinvest += shares_reinvest[t] * price
                val_no_reinvest += shares_no_reinvest[t] * price
            
            # Add Cash Pools to Value
            val_reinvest += cash_reinvest
            
            # Add RF Asset to Value
            val_reinvest += rf_asset_value
            val_no_reinvest += rf_asset_value

            
            # No Reinvest strat has extra cash from dividends
            val_no_reinvest += cash_wallet_no_reinvest
            
            portfolio_reinvest.append(val_reinvest)
            portfolio_no_reinvest.append(val_no_reinvest)
            
            # Ibovespa Value
            if hasattr(self, 'ibov_series') and self.ibov_series is not None:
                 ib_p = self.ibov_series.iloc[i]
                 # If NaN, use last known? Series is ffilled.
                 ib_val = ibov_shares * ib_p
                 ibov_curve.append(ib_val)
            else:
                 ibov_curve.append(0.0)
            
            # Calculate Daily Returns adjusted for Cash Flow
            # r_t = (EndValue - (PrevValue + CashFlow)) / (PrevValue + CashFlow)
            
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
            'Without Reinvestment': portfolio_no_reinvest,
            'Ibovespa': ibov_curve
        }, index=dates)
        
        # Risk Free Comparison
        # Create a series that grows at benchmark_rate from invested_capital stream
        # This is iterative too because of monthly additions
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
            
            # Grow
            if i > 0: # Apply return overnight
                # Using rate for this specific day
                r_day = r_series.get(date, 0.0)
                rf_balance *= (1 + r_day)
            
            rf_curve.append(rf_balance)

            
        self.results['Risk Free'] = rf_curve
        
        # Create Invested Capital Series
        # It changes monthly
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
        """
        Calculates Key Performance Indicators from a daily return series.
        risk_free_series: Array/Series of daily risk free rates (decimal) matching returns.
        """
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

        
        # 5. Max Drawdown
        # Construct a wealth index
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
        """
        Calculates Beta of the portfolio returns against the benchmark (checking Ibovespa first).
        """
        if self.ibov_series is None:
             return 0.0
             
        # Align Series
        # Reconstruct Benchmark Returns
        bench_ret = self.ibov_series.pct_change().dropna()
        port_ret = pd.Series(portfolio_returns, index=self.price_data.index).dropna()
        
        # Inner Join to ensure same dates
        df_join = pd.concat([port_ret, bench_ret], axis=1, join='inner').dropna()
        
        if df_join.empty:
            return 0.0
            
        rp = df_join.iloc[:, 0]
        rb = df_join.iloc[:, 1]
        
        # Beta = Cov(Rp, Rb) / Var(Rb)
        covariance = np.cov(rp, rb)[0, 1]
        variance = np.var(rb)
        
        if variance == 0:
            return 0.0
            
        return covariance / variance

# Example Usage Block
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
