import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt

import valuation
import backtest_tool
import optimization_tool
import market_breadth
import rrg_tool

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")
st.title("📊 Dashboard Financeiro")

tab_val, tab_back, tab_opt, tab_breadth, tab_rrg = st.tabs([
    "Valuation Tab", 
    "Backtest Tab", 
    "Optimization Tab", 
    "Market Breadth", 
    "RRG Tool"
])

with tab_val:
    st.header("Análise de Valuation")
    ticker_val = st.text_input("Insira o Ticker para Valuation:", value="PETR4.SA")
    if st.button("Executar Valuation"):
        with st.spinner("Calculando métricas..."):
            try:
                # Substitua pela chamada da função lógica do seu valuation.py
                # Exemplo: res = valuation.calcular_valuation(ticker_val)
                st.success(f"Valuation executado com sucesso para {ticker_val}!")
            except Exception as e:
                st.error(f"Erro ao processar valuation: {e}")

with tab_back:
    st.header("Backtest de Estratégias")
    ticker_back = st.text_input("Ticker para Backtest:", value="BOVA11.SA")
    data_inicio = st.date_input("Data de Início", value=pd.to_datetime("2020-01-01"))
    if st.button("Rodar Backtest"):
        with st.spinner("Processando histórico..."):
            try:
                # Chamada do seu script backtest_tool.py
                st.success("Backtest concluído.")
            except Exception as e:
                st.error(f"Erro no backtest: {e}")

with tab_opt:
    st.header("Otimização de Carteira")
    tickers_opt = st.text_area("Insira os Tickers separados por linha ou vírgula:", value="PETR4.SA, VALE3.SA, ITUB4.SA")
    if st.button("Otimizar Alocação"):
        with st.spinner("Calculando fronteira eficiente..."):
            try:
                # Chamada do seu script optimization_tool.py
                st.success("Otimização calculada.")
            except Exception as e:
                st.error(f"Erro na otimização: {e}")

with tab_breadth:
    st.header("Market Breadth Indicator")
    if st.button("Carregar Indicadores de Mercado"):
        with st.spinner("Atualizando amplitude de mercado..."):
            try:
                # Chamada do seu script market_breadth.py
                st.success("Market Breadth atualizado.")
            except Exception as e:
                st.error(f"Erro no market breadth: {e}")

with tab_rrg:
    st.header("Relative Rotation Graphs (RRG)")
    if st.button("Gerar Gráfico RRG"):
        with st.spinner("Calculando rotação de ativos..."):
            try:
                # Chamada do seu script rrg_tool.py
                st.success("RRG plotado.")
            except Exception as e:
                st.error(f"Erro no RRG: {e}")