import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


IBOV_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "AXIA3.SA", "RENT3.SA",
    "WEGE3.SA", "BPAC11.SA", "ITSA4.SA", "SUZB3.SA", "HAPV3.SA", "RADL3.SA", "RDOR3.SA", "EQTL3.SA", "PRIO3.SA", "RAIL3.SA", "LREN3.SA", "B3SA3.SA", "GGBR4.SA", "VIVT3.SA", "UGPA3.SA", "CSAN3.SA",
    "BBSE3.SA", "ASAI3.SA", "SBSP3.SA", "CMIG4.SA", "VBBR3.SA", "HYPE3.SA", "CPLE3.SA","TOTS3.SA",
    "EMBJ3.SA", "MULT3.SA", "TIMS3.SA", "PETR3.SA", "BBDC3.SA", "CSNA3.SA", "ENEV3.SA", "MBRF3.SA",
    "CPFE3.SA", "EGIE3.SA", "GOAU4.SA", "KLBN11.SA","ISAE4.SA", "FLRY3.SA", "MRVE3.SA", "CVCB3.SA",
    "YDUQ3.SA", "COGN3.SA"
]

import requests

class BreadthAnalyzer:
    def __init__(self, mode='default', tickers=None, mas=None):
        self.mode = mode
        self.tickers = tickers if tickers is not None else IBOV_TICKERS
        self.data = pd.DataFrame()
        self.mas = mas if mas is not None else [9, 21, 50, 80, 200]
        
    def fetch_all_b3_tickers(self):
        url = "https://www.fundamentus.com.br/resultado.php"
        headers = {'User-Agent': 'Mozilla/5.0'}
        print("Scraping Fundamentus for full active market list...")
        
        try:
            r = requests.get(url, headers=headers)
            df_list = pd.read_html(r.text, decimal=',', thousands='.')
            if len(df_list) > 0:
                df = df_list[0]
                if 'Liq.2meses' in df.columns:
                    df = df[df['Liq.2meses'] > 0]
                
                raw_tickers = df['Papel'].tolist()
                formatted_tickers = [f"{t}.SA" for t in raw_tickers]
                print(f"Found {len(formatted_tickers)} active tickers.")
                return formatted_tickers
        except Exception as e:
            print(f"Error scraping tickers: {e}")
            return IBOV_TICKERS # Fallback

    def fetch_data(self):
        if self.mode == 'full':
            self.tickers = self.fetch_all_b3_tickers()
            
        start_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
        print(f"Fetching data for {len(self.tickers)} stocks...")
        

        try:
            data = yf.download(self.tickers, start=start_date, progress=True)['Close']
            
            data = data.dropna(axis=1, how='all')
            
            self.data = data.ffill()
            
            self.tickers = self.data.columns.tolist()
            return True
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False

    def calculate_breadth(self):

        if self.data.empty:
            success = self.fetch_data()
            if not success:
                return {}, pd.DataFrame()

        results = {}
        last_prices = self.data.iloc[-1]
        
        details = pd.DataFrame(index=self.tickers)
        details['Price'] = last_prices
        
        for ma in self.mas:
            ma_df = self.data.rolling(window=ma).mean()
            last_ma = ma_df.iloc[-1]
            
            above_mask = last_prices > last_ma
            
            valid_count = last_prices.notna() & last_ma.notna()
            total_valid = valid_count.sum()
            
            count = above_mask.sum()
            
            pct = count / total_valid if total_valid > 0 else 0
            results[f"MA{ma}"] = pct
            
            details[f'MA{ma}'] = last_ma
            details[f'Above{ma}'] = above_mask
            
        return results, details
def render():
    st.header("📊 Market Breadth Indicator (Amplitude de Mercado)")
    st.write("Mede a saúde do mercado calculando a percentagem de ações acima das suas médias móveis.")

    col1, col2 = st.columns(2)
    with col1:
        index_choice = st.selectbox("Selecione o Índice Base:", ["IBOVESPA", "Inserir Tickers Manualmente"])
        
    with col2:
        lookback_days = st.number_input("Dias de histórico para o gráfico:", min_value=10, max_value=1000, value=252)

    if index_choice == "IBOVESPA":
        tickers = IBOV_TICKERS
    else:
        raw_tickers = st.text_area("Insira os Tickers separados por vírgula:", value="PETR4, VALE3, ITUB4, BBDC4")
        tickers = []
        for t in raw_tickers.split(","):
            t = t.strip().upper()
            if t:
                if not t.endswith(".SA") and not "." in t and not t.startswith("^") and t[-1].isdigit():
                    t = f"{t}.SA"
                tickers.append(t)

    if st.button("Calcular Market Breadth"):
        with st.spinner("Descarregando dados e calculando médias móveis..."):
            try:
                # Instancia a classe original
                breadth_calc = BreadthAnalyzer(tickers=tickers, mas=[20, 50, 200])
                
                # Força a busca dos dados respeitando a janela de dias solicitada
                end_date = datetime.now()
                start_date = end_date - timedelta(days=int(lookback_days) + 300) # Buffer para médias de 200
                
                breadth_calc.data = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)['Close']
                breadth_calc.data = breadth_calc.data.dropna(how='all').ffill()
                breadth_calc.tickers = breadth_calc.data.columns.tolist()

                # Executa os cálculos
                results, details = breadth_calc.calculate_breadth()

                if not results:
                    st.error("Não foi possível calcular os indicadores com os dados atuais.")
                    return

                # Exibição dos cards de métricas atuais
                st.subheader("Estado Atual do Mercado")
                m1, m2, m3 = st.columns(3)
                m1.metric("Acima de MM20 (Curto Prazo)", f"{results.get('MA20', 0)*100:.1f}%")
                m2.metric("Acima de MM50 (Médio Prazo)", f"{results.get('MA50', 0)*100:.1f}%")
                m3.metric("Acima de MM200 (Longo Prazo)", f"{results.get('MA200', 0)*100:.1f}%")

                # Cálculo do histórico do Breadth para gerar o gráfico temporal
                st.subheader("Evolução Histórica da Amplitude")
                
                hist_breadth = pd.DataFrame(index=breadth_calc.data.index)
                for ma in [20, 50, 200]:
                    ma_df = breadth_calc.data.rolling(window=ma).mean()
                    above = breadth_calc.data > ma_df
                    hist_breadth[f'MM{ma}'] = (above.sum(axis=1) / breadth_calc.data.notna().sum(axis=1)) * 100

                # Corta o dataframe para exibir apenas a janela escolhida pelo usuário
                hist_breadth = hist_breadth.tail(int(lookback_days))

                fig, ax = plt.subplots(figsize=(12, 5))
                ax.plot(hist_breadth.index, hist_breadth['MM20'], label='Acima de MM20', alpha=0.6)
                ax.plot(hist_breadth.index, hist_breadth['MM50'], label='Acima de MM50', linewidth=2)
                ax.plot(hist_breadth.index, hist_breadth['MM200'], label='Acima de MM200', linewidth=2, color='black')
                
                ax.axhline(80, color='red', linestyle='--', alpha=0.5, label='Sobrecomprado (80%)')
                ax.axhline(20, color='green', linestyle='--', alpha=0.5, label='Sobrevendido (20%)')
                
                ax.set_title("Percentagem de Ativos Acima da Média Móvel")
                ax.set_ylabel("% de Ativos")
                ax.legend(loc='upper left')
                ax.grid(True, linestyle='--', alpha=0.3)
                
                st.pyplot(fig)

                # Tabela detalhada individual
                st.subheader("Visão Detalhada por Ativo")
                details_display = details.copy()
                for ma in [20, 50, 200]:
                    details_display[f'Above{ma}'] = details_display[f'Above{ma}'].map({True: "🟢 Sim", False: "🔴 Não"})
                st.dataframe(details_display[['Price', 'Above20', 'Above50', 'Above200']], use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao processar o Market Breadth: {str(e)}")