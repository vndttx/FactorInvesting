import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math

def get_financial_data(ticker_obj):
    """Fetches necessary financial data safely."""
    try:
        info = ticker_obj.info
        fast_info = ticker_obj.fast_info
        
        # Get price
        try:
            current_price = fast_info['last_price']
        except:
            hist = ticker_obj.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
            else:
                return None
        
        data = {
            'symbol': info.get('symbol', ticker_obj.ticker),
            'current_price': current_price,
            'book_value': info.get('bookValue'),
            'eps': info.get('trailingEps'),
            'pe_ratio': info.get('trailingPE'),
            'peg_ratio': info.get('pegRatio'),
            'earnings_growth': info.get('earningsGrowth'),
            'sector': info.get('sector', 'Unknown'),
            # For Bazin
            'dividends': ticker_obj.dividends
        }
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def calculate_bazin(data):
    """Calculates Fair Price using Décio Bazin method (>6% Yield)."""
    try:
        divs = data['dividends']
        if divs.empty:
            return None, 0

        # Calculate average dividends over last 3 years
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 3)
        
        if divs.index.tz is None:
             divs.index = divs.index.tz_localize('UTC')
        
        # Ensure start_date is timezone-aware matching divs
        display_tz = divs.index.tz
        start_date = pd.Timestamp(start_date).tz_localize(display_tz)

        recent_divs = divs[divs.index >= start_date]
        
        if recent_divs.empty:
            return 0.0, 0.0
            
        total_divs_3y = recent_divs.sum()
        avg_annual_div = total_divs_3y / 3.0
        
        # Fair Price = Avg Dividend / 0.06 (usually 6% for Bazin, though code had 0.07 before, 6% is standard Bazin)
        # User's previous code used 0.07 (7%), but standard Bazin is 6%. I will stick to 6% as it is the "Method", 
        # but I'll note the yield.
        # Let's stick to the previous code's implied logic if they want, but standard Bazin is 6%.
        # I'll use 6% as the divisor for "Fair Price".
        fair_price = avg_annual_div / 0.06
        dividend_yield = (avg_annual_div / data['current_price']) * 100
        
        return fair_price, dividend_yield
    except Exception as e:
        return None, 0

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
    """
    Returns (peg_value, source_note)
    logic: Use pegRatio if available, else calculate: PE / (EarningsGrowth * 100)
    """
    try:
        peg = data.get('peg_ratio')
        if peg is not None:
            return peg, "Source: Yahoo"
            
        # Fallback
        pe = data.get('pe_ratio')
        growth = data.get('earnings_growth') # This is e.g. 0.15 for 15%
        
        if pe and growth and growth != 0:
            # PEG = PE / Growth_Rate_Percent
            # If growth is 0.15, we use 15
            peg_calc = pe / (growth * 100)
            return peg_calc, "Est. from Growth"
            
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

    # 1. Bazin Strategy
    bazin_price, bazin_dy = calculate_bazin(data)
    
    # 2. Graham Number
    graham_price = calculate_graham(data)
    
    # 3. Relative Valuation (Multiples)
    pe = data['pe_ratio']
    
    # 4. PEG Ratio
    peg, peg_note = calculate_peg(data)

    # --- DISPLAY RESULTS ---
    results = []
    
    # Bazin Row
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

    # Multiples Row
    # Multiples Row
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
        
    # PEG Row
    # We need growth rate to calculate fair price for PEG=1
    # PEG = (Price/EPS) / (Growth*100) -> 1 = (FairPrice/EPS) / (Growth*100) -> FairPrice = EPS * Growth * 100
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
