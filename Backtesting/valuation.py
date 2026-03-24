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
                        # Cálculo Year-over-Year (Ano atual vs Ano anterior)
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
            'earnings_growth': growth, # Agora com fallback manual
            'sector': info.get('sector', 'Unknown'),
            'dividends': ticker_obj.dividends
        }
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def calculate_bazin(data):
    """Cálculo de Bazin otimizado com agregação do Pandas."""
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
    """Calculates Benjamin Graham Number: Sqrt(22.5 * EPS * BVPS)."""
    try:
        eps = data['eps']
        bvps = data['book_value']
        
        if eps is None or bvps is None or eps < 0 or bvps < 0:
            return None
            
        graham_num = math.sqrt(22.5 * eps * bvps)
        return graham_num
    except:
        return None

def calculate_peg(data):
    try:
        if data.get('peg_ratio') is not None:
            return data['peg_ratio'], "Yahoo API"
            
        pe = data.get('pe_ratio')
        growth = data.get('earnings_growth')
        
        if pe and growth and growth > 0:
            peg_calc = pe / (growth * 100)
            return peg_calc, "Manual Growth Calc"
            
        return None, None
    except:
        return None, None

def analyze_valuation():
    print("=== Multi-Method Valuation Tool ===")
    ticker_input = input("Enter Brazilian Stock Ticker (e.g., PETR4): ").strip().upper()
    
    if not ticker_input:
        print("No ticker provided.")
        return

    if not ticker_input.endswith(".SA"):
        ticker = f"{ticker_input}.SA"
    else:
        ticker = ticker_input

    print(f"\nFetching data for {ticker}...")
    stock = yf.Ticker(ticker)
    data = get_financial_data(stock)
    
    if not data:
        print("Could not retrieve sufficient data.")
        return

    print(f"\nAnalyzing {data['symbol']} (Sector: {data['sector']})")
    print(f"Current Price: R$ {data['current_price']:.2f}")
    print("-" * 50)

    bazin_price, bazin_dy = calculate_bazin(data)
    graham_price = calculate_graham(data)
    pe = data['pe_ratio']
    peg, peg_note = calculate_peg(data)
    results = []
    

    if bazin_price:
        upside = ((bazin_price - data['current_price']) / data['current_price']) * 100
        status = "Cheap" if bazin_price > data['current_price'] else "Expensive"
        results.append(["Décio Bazin (Div Yield)", f"R$ {bazin_price:.2f}", f"{upside:+.2f}%", status, f"Avg Yield: {bazin_dy:.2f}% (Target 6%)"])
    else:
        results.append(["Décio Bazin (Div Yield)", "N/A", "-", "-", " insufficient dividend history"])

    # Graham Row
    if graham_price:
        upside = ((graham_price - data['current_price']) / data['current_price']) * 100
        status = "Cheap" if graham_price > data['current_price'] else "Expensive"
        results.append(["Graham Number", f"R$ {graham_price:.2f}", f"{upside:+.2f}%", status, "Based on EPS & BVPS"])
    else:
        results.append(["Graham Number", "N/A", "-", "-", "Neg. Earnings or Book Value"])

    pe = data.get('pe_ratio')
    eps = data.get('eps')
    if pe and eps:
        # Fair Price = 15 * EPS
        fair_price_pe = 15 * eps
        upside_pe = ((fair_price_pe - data['current_price']) / data['current_price']) * 100
        status_pe = "Cheap" if fair_price_pe > data['current_price'] else "Expensive"
        results.append(["P/E Ratio", f"{pe:.2f}x", f"{upside_pe:+.2f}%", status_pe, "Target PE: 15x"])
    else:
        results.append(["P/E Ratio", "N/A", "-", "-", "-"])
        
    growth = data.get('earnings_growth')
    
    if peg:
        peg_upside_str = "-"
        if eps and growth:
            fair_price_peg = eps * (growth * 100)
            peg_upside = ((fair_price_peg - data['current_price']) / data['current_price']) * 100
            peg_upside_str = f"{peg_upside:+.2f}%"
            
        status = "Undervalued" if peg < 1 else "Overvalued"
        results.append(["PEG Ratio", f"{peg:.2f}", peg_upside_str, status, f"< 1.0 ideal ({peg_note})"])
    else:
        results.append(["PEG Ratio", "N/A", "-", "-", "-"])

    # Print Table
    row_format = "{:<25} {:<15} {:<15} {:<15} {:<25}"
    print(row_format.format("METHOD", "IMPLIED VALUE", "UPSIDE", "STATUS", "NOTES"))
    print("-" * 100)
    for row in results:
        print(row_format.format(*row))
    print("-" * 100)

if __name__ == "__main__":
    analyze_valuation()
