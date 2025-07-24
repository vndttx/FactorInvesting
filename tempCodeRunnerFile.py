import pandas as pd
import quantstats as qs
import yfinance as yf
import bt as bt
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
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
         
dados_empresas = filtrar(dados_empresas)
dados_empresas = classificar(dados_empresas)
dados_empresas = ranking_geral(dados_empresas)

print(dados_empresas)
