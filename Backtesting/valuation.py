import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math

def get_financial_data(ticker_obj):
    try:
        info = ticker_obj.info
        fast_info = ticker_obj.fast_info
        
        try:
            current_price = fast_info['last_price']
        except:
            hist = ticker_obj.history(period="1d")
            current_price = hist['Close'].iloc[-1] if not hist.empty else None
        
        growth = info.get('earningsGrowth')
        if growth is None:
            try:
                financials = ticker_obj.financials
                if not financials.empty and 'Net Income' in financials.index:
                    net_income = financials.loc['Net Income']
                    if len(net_income) >= 2:
                        growth = (net_income.iloc[0] - net_income.iloc[1]) / abs(net_income.iloc[1])
            except:
                growth = None
        
        data = {
            'symbol': info.get('symbol', ticker_obj.ticker),
            'current_price': current_price,
            'book_value': info.get('bookValue'),
            'eps': info.get('trailingEps'),
            'pe_ratio': info.get('trailingPE'),
            'peg_ratio': info.get('pegRatio'),
            'earnings_growth': growth,
            'sector': info.get('sector', 'Unknown'),
            'dividends': ticker_obj.dividends
        }
        return data
    except Exception:
        return None

def calculate_bazin(data):
    divs = data['dividends']
    if divs.empty:
        return None, 0
    three_years_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=3)
    recent_divs = divs[divs.index >= three_years_ago]
    if recent_divs.empty: return 0.0, 0.0
    avg_annual_div = recent_divs.sum() / 3.0
    fair_price = avg_annual_div / 0.06
    yield_on_cost = (avg_annual_div / data['current_price']) * 100
    return fair_price, yield_on_cost

def calculate_graham(data):
    try:
        eps = data['eps']
        bvps = data['book_value']
        if eps is None or bvps is None or eps < 0 or bvps < 0:
            return None
        return math.sqrt(22.5 * eps * bvps)
    except:
        return None

def calculate_peg(data):
    try:
        if data.get('peg_ratio') is not None:
            return data['peg_ratio']
        pe = data.get('pe_ratio')
        growth = data.get('earnings_growth')
        if pe and growth and growth > 0:
            return pe / (growth * 100)
        return None
    except:
        return None

def analyze_valuation():
    print("=== Multi-Stock Valuation Comparison ===")
    user_input = input("Enter up to 4 Brazilian Tickers separated by space (e.g., PETR4 VALE3 ITUB4): ").strip().upper()
    
    ticker_list = user_input.split()[:4]
    if not ticker_list:
        print("No tickers provided.")
        return

    comparison_data = []

    for t in ticker_list:
        symbol = t if t.endswith(".SA") else f"{t}.SA"
        print(f"Fetching {symbol}...")
        stock = yf.Ticker(symbol)
        data = get_financial_data(stock)
        
        if data:
            bazin_p, _ = calculate_bazin(data)
            graham_p = calculate_graham(data)
            peg_v = calculate_peg(data)
            
            comparison_data.append({
                'Ticker': data['symbol'].replace('.SA', ''),
                'Price': f"R$ {data['current_price']:.2f}",
                'Bazin': f"R$ {bazin_p:.2f}" if bazin_p else "N/A",
                'Graham': f"R$ {graham_p:.2f}" if graham_p else "N/A",
                'P/E': f"{data['pe_ratio']:.2f}x" if data['pe_ratio'] else "N/A",
                'PEG': f"{peg_v:.2f}" if peg_v else "N/A"
            })

    if not comparison_data:
        print("No valid data found.")
        return

    print("\n" + "="*85)
    row_format = "{:<12} | {:<12} | {:<12} | {:<12} | {:<12} | {:<12}"
    print(row_format.format("TICKER", "PRICE", "BAZIN", "GRAHAM", "P/E", "PEG"))
    print("-" * 85)
    
    for row in comparison_data:
        print(row_format.format(
            row['Ticker'], row['Price'], row['Bazin'], 
            row['Graham'], row['P/E'], row['PEG']
        ))
    print("="*85)

if __name__ == "__main__":
    analyze_valuation()