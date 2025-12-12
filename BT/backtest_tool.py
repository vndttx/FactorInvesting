import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class PortfolioBacktester:
    def __init__(self, tickers, initial_investment, monthly_investment, start_date, end_date=None, benchmark_rate=0.10):
        """
        initial_investment: Amount in BRL
        monthly_investment: Amount in BRL
        benchmark_rate: Annual risk-free rate (decimal, e.g., 0.10 for 10%)
        """
        self.tickers = tickers
        self.initial_investment = initial_investment
        self.monthly_investment = monthly_investment
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.benchmark_rate = benchmark_rate
        self.data = pd.DataFrame()
        self.dividends = pd.DataFrame()
        self.currency = pd.DataFrame()
        self.price_data = None
        self.div_data = None
        
    def fetch_data(self):
        print("Fetching data...")
        # Add currency if there are US stocks (assuming US stocks don't have .SA)
        us_stocks = [t for t in self.tickers if not t.endswith('.SA')]
        
        # Download Stock Data
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date, actions=True)
        
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
        self.div_data = self.div_data.loc[self.price_data.index].fillna(0)
        
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
        
        # 2. Strategy: No Reinvest (Take Dividends as Cash)
        shares_no_reinvest = {t: 0.0 for t in self.tickers}
        cash_wallet_no_reinvest = 0.0 # Accumulated dividends
        cash_residual_no_reinvest = 0.0 # Small amounts from buying
        portfolio_no_reinvest = [] # Total Wealth (Shares + Cash Wallet)
        
        # Track monthly contributions
        last_month = dates[0].month
        
        # Initial Deposit
        cash_reinvest += self.initial_investment
        cash_residual_no_reinvest += self.initial_investment
        invested_capital += self.initial_investment
        
        # Distribute initial cash equally
        weight = 1.0 / len(self.tickers)
        
        for t in self.tickers:
            price = self.price_data.iloc[0][t]
            if not pd.isna(price) and price > 0:
                # Buy for Reinvest Strat
                alloc = self.initial_investment * weight
                bought = alloc / price
                shares_reinvest[t] += bought
                cash_reinvest -= alloc # Simplified: assume fractional shares or full usage
                # Better: cash_reinvest -= bought * price (results in ~0)
                
                # Buy for No Reinvest Strat
                shares_no_reinvest[t] += bought
                cash_residual_no_reinvest -= alloc

        # Fix floating point drift or assume strictly 0 if we assume fractional shares allowed
        # To be precise let's just assume we track Value directly: Value = Shares * Price + Cash
        # But for Dividends logic we need Shares count.
        
        for i in range(n_days):
            date = dates[i]
            prices = self.price_data.iloc[i]
            divs = self.div_data.iloc[i]
            
            # Check for Monthly Contribution
            # Simple logic: if month changed, add money
            # (Skip first day as it was initial)
            if i > 0 and date.month != last_month:
                invested_capital += self.monthly_investment
                
                # Add to both strategies
                to_invest = self.monthly_investment
                
                # Buy Stocks (Equal Weight)
                for t in self.tickers:
                    price = prices[t]
                    if not pd.isna(price) and price > 0:
                        alloc = to_invest * weight
                        
                        # Reinvest Strat
                        bought = alloc / price
                        shares_reinvest[t] += bought
                        
                        # No Reinvest Strat
                        shares_no_reinvest[t] += bought
                
                last_month = date.month
            
            # Handle Dividends
            # Reinvest Strat: Divs -> Buy Shares
            for t in self.tickers:
                d_per_share = divs[t]
                if d_per_share > 0:
                    # REINVEST
                    # Total Div Received
                    payout_r = shares_reinvest[t] * d_per_share
                    # Buy more of same stock
                    if prices[t] > 0:
                        new_shares = payout_r / prices[t]
                        shares_reinvest[t] += new_shares
                    
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
            
            # No Reinvest strat has extra cash from dividends
            val_no_reinvest += cash_wallet_no_reinvest
            
            portfolio_reinvest.append(val_reinvest)
            portfolio_no_reinvest.append(val_no_reinvest)
            
        self.results = pd.DataFrame({
            'With Reinvestment': portfolio_reinvest,
            'Without Reinvestment': portfolio_no_reinvest
        }, index=dates)
        
        # Risk Free Comparison
        # Create a series that grows at benchmark_rate from invested_capital stream
        # This is iterative too because of monthly additions
        rf_balance = 0.0
        rf_curve = []
        
        last_m = dates[0].month
        rf_added_initial = False
        
        # Daily rate
        daily_rate = (1 + self.benchmark_rate) ** (1/252) - 1
        
        rf_balance = self.initial_investment
        
        for i in range(n_days):
            date = dates[i]
            if i > 0 and date.month != last_m:
                 rf_balance += self.monthly_investment
                 last_m = date.month
            
            # Grow
            if i > 0: # Apply return overnight
                rf_balance *= (1 + daily_rate)
            
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
        
    def plot(self):
        plt.figure(figsize=(12, 6))
        plt.plot(self.results.index, self.results['With Reinvestment'], label='With Dividends Reinvested')
        plt.plot(self.results.index, self.results['Without Reinvestment'], label='Without Reinvestment (Divs kept in Cash)')
        plt.plot(self.results.index, self.results['Risk Free'], label=f'Risk Free ({self.benchmark_rate*100}%)', linestyle='--')
        
        plt.title('Portfolio Backtest Performance (BRL)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value (BRL)')
        plt.legend()
        plt.grid(True)
        plt.show()

# Example Usage Block
if __name__ == "__main__":
    # Example Inputs
    tickers = ['BBAS3.SA', 'CMIG4.SA', 'CSMG3.SA', 'VIVT3.SA', 'ITUB4.SA'] # Mix of BR and US
    initial = 1000
    monthly = 5000
    start = '2015-01-01'
    
    bt = PortfolioBacktester(tickers, initial, monthly, start)
    bt.run()
    bt.plot()
    
    print("Final Values:")
    print(bt.results.iloc[-1])
