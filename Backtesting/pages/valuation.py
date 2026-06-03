import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import math
import streamlit as st

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

def render():
    st.header("Multi-Stock Valuation Comparison")
    
    user_input = st.text_input(
        "Insira até 4 tickers brasileiros separados por espaço (ex: PETR4 VALE3 ITUB4):", 
        value="PETR4 VALE3 ITUB4"
    ).strip().upper()
    
    if st.button("Executar Análise de Valuation"):
        ticker_list = user_input.split()[:4]
        if not ticker_list:
            st.warning("Nenhum ticker foi fornecido.")
            return

        comparison_data = []

        with st.spinner("Procurando dados no Yahoo Finance..."):
            for t in ticker_list:
                symbol = t if t.endswith(".SA") else f"{t}.SA"
                stock = yf.Ticker(symbol)
                data = get_financial_data(stock)
                
                if data:
                    bazin_p, _ = calculate_bazin(data)
                    graham_p = calculate_graham(data)
                    peg_v = calculate_peg(data)
                    
                    comparison_data.append({
                        'Ticker': data['symbol'].replace('.SA', ''),
                        'Preço Atual': f"R$ {data['current_price']:.2f}" if data['current_price'] else "N/A",
                        'Preço Justo Bazin': f"R$ {bazin_p:.2f}" if bazin_p else "N/A",
                        'Preço Justo Graham': f"R$ {graham_p:.2f}" if graham_p else "N/A",
                        'P/L': f"{data['pe_ratio']:.2f}x" if data['pe_ratio'] else "N/A",
                        'PEG Ratio': f"{peg_v:.2f}" if peg_v else "N/A"
                    })

        if not comparison_data:
            st.error("Nenhum dado válido encontrado para os tickers informados.")
            return

        df_result = pd.DataFrame(comparison_data)
        st.subheader("Resultados Comparativos")
        st.dataframe(df_result, use_container_width=True, hide_index=True)