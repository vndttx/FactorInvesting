import pandas as pd
import quantstats as qs
import yfinance as yf
import bt as bt
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
plt.style.use("dark_background")

dados_empresas = pd.read_excel("statusinvest-busca-avancada.xlsx")

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
