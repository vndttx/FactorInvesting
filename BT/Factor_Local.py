import pandas as pd
import quantstats as qs
import yfinance as yf
import bt as bt
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
import datetime
from datetime import datetime, timedelta
plt.style.use("dark_background")

# Top 50 IBOV components (Approximate list for simulation)
top_50_tickers = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "PETR3.SA", "BBDC4.SA", "ELET3.SA", "BBAS3.SA", "WEGE3.SA", 
    "ITSA4.SA", "RENT3.SA", "BPAC11.SA", "SUZB3.SA", "HAPV3.SA", "PRIO3.SA", "RDOR3.SA", "RADL3.SA", 
    "GGBR4.SA", "UGPA3.SA", "CSAN3.SA", "VBBR3.SA", "B3SA3.SA", "JBSS3.SA", "SBSP3.SA", "VIVT3.SA", 
    "BBSE3.SA", "TIMS3.SA", "RAIL3.SA", "CMIG4.SA", "CPLE6.SA", "EQTL3.SA", "LREN3.SA", "MGLU3.SA", 
    "ASAI3.SA", "HYPE3.SA", "TOTS3.SA", "CSNA3.SA", "USIM5.SA", "EMBR3.SA", "GOAU4.SA", "CCRO3.SA", 
    "ENEV3.SA", "EGIE3.SA", "CPFE3.SA", "BRFS3.SA", "KLBN11.SA", "BRKM5.SA", "CRFB3.SA", "PCAR3.SA", 
    "AZUL4.SA", "CVCB3.SA"
]

def fetch_market_data(tickers):
    print(f"Fetching fundamental data for {len(tickers)} tickers. This may take a moment...")
    data_list = []
    
    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            info = ticker.info
            
            # Map YF info to script columns
            current_price = info.get('currentPrice', 0)
            avg_volume = info.get('averageVolume', 0)
            
            # Safely get values, defaulting to 0
            market_cap = info.get('marketCap', 0)
            liquidity = avg_volume * current_price if current_price else 0
            net_margin = info.get('profitMargins', 0)
            gross_margin = info.get('grossMargins', 0)
            op_margin = info.get('operatingMargins', 0)
            rev_growth = info.get('revenueGrowth', 0)
            earnings_growth = info.get('earningsGrowth', 0)
            roe = info.get('returnOnEquity', 0)
            current_ratio = info.get('currentRatio', 0)
            peg_ratio = info.get('pegRatio', 0)
            price_to_book = info.get('priceToBook', 0)
            pe_ratio = info.get('trailingPE', 0)
            price_to_sales = info.get('priceToSalesTrailing12Months', 0)
            eps = info.get('trailingEps', 0)
            
            # P/EBIT Calculation: Market Cap / EBIT
            # EBIT ~ Revenue * Operating Margin
            revenue = info.get('totalRevenue', 0)
            ebit = revenue * op_margin if revenue and op_margin else 0
            p_ebit = market_cap / ebit if ebit else 0
            
            data_list.append({
                'TICKER': t, 
                'TICKER_CLEAN': t.replace('.SA', ''),
                ' VALOR DE MERCADO': market_cap,
                ' LIQUIDEZ MEDIA DIARIA': liquidity,
                'MARG. LIQUIDA': net_margin,
                'MARGEM BRUTA': gross_margin,
                'MARGEM EBIT': op_margin,
                'CAGR RECEITAS 5 ANOS': rev_growth,
                'CAGR LUCROS 5 ANOS': earnings_growth,
                'ROE': roe,
                'LIQ. CORRENTE': current_ratio,
                ' PEG Ratio': peg_ratio,
                'P/VP': price_to_book,
                'P/L': pe_ratio,
                'PSR': price_to_sales,
                'P/EBIT': p_ebit,
                ' LPA': eps
            })
        except Exception as e:
            print(f"Failed to fetch {t}: {e}")
            
    df = pd.DataFrame(data_list)
    # Rename for compatibility with line 45/60
    df = df.rename(columns={'TICKER_CLEAN': 'TICKER'})
    return df

# dados_empresas = pd.read_excel("indicadores-julho.xlsx")
dados_empresas = fetch_market_data(top_50_tickers)

def filtrar(dados_empresas):
    dados_empresas = dados_empresas[dados_empresas[' VALOR DE MERCADO'] > 50000000];
    dados_empresas = dados_empresas[dados_empresas[' LIQUIDEZ MEDIA DIARIA'] > 1000000];
    dados_empresas = dados_empresas[dados_empresas['MARG. LIQUIDA'] >= 0.05];
    dados_empresas = dados_empresas[dados_empresas['MARGEM BRUTA'] >= 0.05];
    dados_empresas = dados_empresas[dados_empresas['MARGEM EBIT'] >= 0.05];
    dados_empresas = dados_empresas[dados_empresas['CAGR RECEITAS 5 ANOS'] >= 0.05];
    dados_empresas = dados_empresas[dados_empresas['CAGR LUCROS 5 ANOS'] >= 0.05];
    dados_empresas = dados_empresas[dados_empresas['ROE'] >= 0.05];
    dados_empresas = dados_empresas[dados_empresas['LIQ. CORRENTE'] != 0];
    dados_empresas = dados_empresas[dados_empresas[' PEG Ratio'] >= 0.05];
    dados_empresas = dados_empresas[dados_empresas['P/VP'] <= 2];
    dados_empresas.fillna(0, inplace=True);
    return dados_empresas

def classificar(dados_empresas):
    dados_empresas['ranking_margem_liq'] = dados_empresas['MARG. LIQUIDA'].rank(ascending = False);
    dados_empresas['ranking_pl'] = dados_empresas['P/L'].rank(ascending = True);dados_empresas['ranking_psr'] = dados_empresas['PSR'].rank(ascending = False);
    dados_empresas['ranking_roe'] = dados_empresas['ROE'].rank(ascending = False);
    dados_empresas['ranking_p_ebit'] = dados_empresas['P/EBIT'].rank(ascending = True);
    dados_empresas['ranking_lpa'] = dados_empresas[' LPA'].rank(ascending = False);
    dados_empresas['ranking_liq_corr'] = dados_empresas['LIQ. CORRENTE'].rank(ascending = False);
    dados_empresas['ranking_mktValue'] = dados_empresas[' VALOR DE MERCADO'].rank(ascending = False);
    return dados_empresas

def ranking_geral(dados_empresas):
    dados_empresas['ranking_final'] = dados_empresas['ranking_margem_liq'] + dados_empresas['ranking_psr'] + dados_empresas['ranking_roe'] + dados_empresas['ranking_liq_corr'] + dados_empresas['ranking_lpa'] + dados_empresas['ranking_p_ebit'] + dados_empresas['ranking_pl'] + dados_empresas['ranking_mktValue']
    dados_empresas['ranking_final'] = dados_empresas['ranking_final'].rank()  
    return dados_empresas

def lista_tickers(dados_empresas):
    dados_empresas = dados_empresas[dados_empresas['ranking_final'] <= 10]
    dados_empresas = dados_empresas["TICKER"]
    return dados_empresas  
         
dados_empresas = filtrar(dados_empresas)
dados_empresas = classificar(dados_empresas)
dados_empresas = ranking_geral(dados_empresas)
dados_empresas = lista_tickers(dados_empresas)


inicio = "1999-01-01"
today = datetime.now()
fim = today - pd.tseries.offsets.BusinessDay(3)
fim = fim.strftime("%Y-%m-%d")

tickers = pd.Series(dados_empresas).tolist()
tickers = [ticker + ".SA" for ticker in tickers]
data = yf.download(tickers, start=inicio, end=fim).dropna()
data = data["Close"]

simulacao = bt.get(tickers, start = inicio, end = fim)

pesosIguais = bt.Strategy('simulacao', [bt.algos.RunMonthly(),bt.algos.SelectAll(),bt.algos.WeighEqually(),bt.algos.Rebalance()])

teste = bt.Backtest(pesosIguais, simulacao)

resultado = bt.run(teste)

plt.ioff()

resultado.plot()

plt.show()

print(tickers)
