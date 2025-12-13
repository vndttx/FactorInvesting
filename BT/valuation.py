import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def analyze_stock_bazin():
    print("=== Décio Bazin Valuation Tool ===")
    ticker_input = input("Enter Brazilian Stock Ticker (e.g., PETR4): ").strip().upper()
    
    if not ticker_input:
        print("No ticker provided.")
        return

    if not ticker_input.endswith(".SA"):
        ticker = f"{ticker_input}.SA"
    else:
        ticker = ticker_input

    print(f"\nFetching data for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        
        try:
            current_price = stock.fast_info['last_price']
        except:
             # Fallback
             hist = stock.history(period="1d")
             if hist.empty:
                 print(f"Error: Could not fetch price data for {ticker}. Is the ticker correct?")
                 return
             current_price = hist['Close'].iloc[-1]

        divs = stock.dividends
        
        if divs.empty:
            print(f"No dividend history found for {ticker}.")
            return

        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 3)
        
        if divs.index.tz is None:
             divs.index = divs.index.tz_localize('UTC')
        
        start_date = pd.Timestamp(start_date).tz_localize(divs.index.tz)
        
        recent_divs = divs[divs.index >= start_date]
        
        if recent_divs.empty:
             print(f"No dividends paid in the last 3 years by {ticker}.")
             return
             
        total_divs_3y = recent_divs.sum()
        avg_annual_div = total_divs_3y / 3.0
        
        fair_price = avg_annual_div / 0.07
        
        dy_current = (avg_annual_div / current_price) * 100
        
        print("\n" + "="*40)
        print(f" ANALYSIS: {ticker}")
        print("="*40)
        print(f"Current Price          : R$ {current_price:.2f}")
        print(f"Avg Annual Div (3y)    : R$ {avg_annual_div:.2f}")
        print(f"Implied Div Yield      : {dy_current:.2f}% (Target: >7%)")
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
