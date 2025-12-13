import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def analyze_stock_bazin():
    print("=== Décio Bazin Valuation Tool ===")
    ticker_input = input("Enter Brazilian Stock Ticker (e.g., PETR4): ").strip().upper()
    
    if not ticker_input:
        print("No ticker provided.")
        return

    # Auto-append .SA if missing and if it looks like a BR stock (usually 4-5 chars + optional suffix)
    if not ticker_input.endswith(".SA"):
        ticker = f"{ticker_input}.SA"
    else:
        ticker = ticker_input

    print(f"\nFetching data for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Get Current Price
        # fast_info is usually faster and more reliable for current price than history
        try:
            current_price = stock.fast_info['last_price']
        except:
             # Fallback
             hist = stock.history(period="1d")
             if hist.empty:
                 print(f"Error: Could not fetch price data for {ticker}. Is the ticker correct?")
                 return
             current_price = hist['Close'].iloc[-1]

        # 2. Get Dividend History
        divs = stock.dividends
        
        if divs.empty:
            print(f"No dividend history found for {ticker}.")
            return

        # Filter for last 3 years for consistency
        # Bazin suggests searching for companies paying > 6% consistently
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 3)
        
        # Ensure timezone awareness compatibility
        if divs.index.tz is None:
             divs.index = divs.index.tz_localize('UTC') # Assume UTC if naive, usually yf is timezone aware
        
        # Convert start_date to match div index tz
        start_date = pd.Timestamp(start_date).tz_localize(divs.index.tz)
        
        recent_divs = divs[divs.index >= start_date]
        
        if recent_divs.empty:
             print(f"No dividends paid in the last 3 years by {ticker}.")
             return
             
        # Calculate Average Annual Dividend
        # We sum all dividends in the 3 year period and divide by 3
        total_divs_3y = recent_divs.sum()
        avg_annual_div = total_divs_3y / 3.0
        
        # 3. Calculate Fair Price (Preço Teto)
        # Bazin Fair Price = Avg Annual Div / 0.06
        fair_price = avg_annual_div / 0.06
        
        # 4. Calculate Dividend Yield (Current)
        dy_current = (avg_annual_div / current_price) * 100
        
        # Output Analysis
        print("\n" + "="*40)
        print(f" ANALYSIS: {ticker}")
        print("="*40)
        print(f"Current Price          : R$ {current_price:.2f}")
        print(f"Avg Annual Div (3y)    : R$ {avg_annual_div:.2f}")
        print(f"Implied Div Yield      : {dy_current:.2f}% (Target: >6%)")
        print("-" * 40)
        print(f"Bazin Fair Price (Teto): R$ {fair_price:.2f}")
        print("-" * 40)
        
        if current_price < fair_price:
            margin = ((fair_price - current_price) / current_price) * 100
            print(f"RESULT: ATTRACTIVE")
            print(f"Discount to Fair Price : {margin:.2f}%")
        else:
            premium = ((current_price - fair_price) / fair_price) * 100
            print(f"RESULT: UNATTRACTIVE / EXPENSIVE")
            print(f"Premium over Fair Price: {premium:.2f}%")
            
        print("="*40 + "\n")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    analyze_stock_bazin()
