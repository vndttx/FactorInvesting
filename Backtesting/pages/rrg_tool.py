import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

class RRGCalculator:
    def __init__(self, tickers, benchmark, start_date, window=14):
        self.tickers = tickers
        self.benchmark = benchmark
        self.start_date = start_date
        self.window = window
        self.data = None
        self.rrg_history = None

    def fetch_data(self):
        """Fetches data from Yahoo Finance."""
        all_symbols = self.tickers + [self.benchmark]
        print(f"Fetching data for RRG: {all_symbols}")
        
        df = yf.download(all_symbols, start=self.start_date, progress=False, auto_adjust=True)
        
        if isinstance(df.columns, pd.MultiIndex):
            if 'Close' in df.columns.get_level_values(0):
                 df = df['Close']
            
        df = df.dropna(how='all')
        
        df = df.ffill()
        
        if self.benchmark not in df.columns:
            raise ValueError(f"Benchmark {self.benchmark} not found in fetched data.")
            
        self.data = df
        return df

    def calculate_rrg_metrics(self, price_data, benchmark_data, window_ratio=14, window_mom=14):
        rs_series = price_data.div(benchmark_data, axis=0)
        std_rs = rs_series.rolling(window=window_ratio).std()
        rs_ratio = 100 + ((rs_series - ema_rs) / std_rs) * 1
        rs_mom = 100 + (rs_ratio.pct_change(periods=window_mom) * 100)
        return rs_ratio.ffill(), rs_mom.ffill()

    def calculate(self):
        """Calculates JdK RS-Ratio and RS-Momentum."""
        if self.data is None:
            self.fetch_data()
            
        df = self.data
        bench_series = df[self.benchmark]
        
        results = {}
        
        for ticker in self.tickers:
            if ticker not in df.columns:
                continue
            rs = 100 * (df[ticker] / bench_series)
            

            rs_mean = rs.rolling(window=self.window).mean()
            rs_std = rs.rolling(window=self.window).std(ddof=0)
            

            rs_std = rs_std.replace(0, np.nan)
            
            jdk_rs_ratio = 100 + ((rs - rs_mean) / rs_std)

            roc = jdk_rs_ratio.diff()
            
            roc_mean = roc.rolling(window=self.window).mean()
            roc_std = roc.rolling(window=self.window).std(ddof=0)
            roc_std = roc_std.replace(0, np.nan)
            
            jdk_rs_momentum = 100 + ((roc - roc_mean) / roc_std)

            ticker_df = pd.DataFrame({
                'RS_Ratio': jdk_rs_ratio,
                'RS_Momentum': jdk_rs_momentum
            })
            
            results[ticker] = ticker_df
            
        self.rrg_history = results
        return results

    def get_latest_values(self):
        """Returns the latest Ratio/Momentum for scatter plot."""
        if not self.rrg_history:
            return {}
            
        latest = {}
        for ticker, df in self.rrg_history.items():
            if not df.empty:
                row = df.iloc[-1]
                latest[ticker] = {
                    'RS_Ratio': row['RS_Ratio'],
                    'RS_Momentum': row['RS_Momentum']
                }
        return latest
        
    def get_trails(self, length=10):
        """Returns the last N points for plotting trails."""
        if not self.rrg_history:
            return {}
            
        trails = {}
        for ticker, df in self.rrg_history.items():
            if not df.empty:
                # Get last 'length' rows
                trails[ticker] = df.tail(length)
        return trails
    import streamlit as st
import matplotlib.pyplot as plt

def render():
    st.header("🌀 Relative Rotation Graphs (RRG)")
    st.write("Visualize o momento e a força relativa de um grupo de ativos contra um benchmark.")

    col1, col2 = st.columns(2)
    with col1:
        raw_tickers = st.text_input("Ativos (separados por vírgula):", value="PETR4.SA, VALE3.SA, ITUB4.SA, BBDC4.SA, WEGE3.SA")
        benchmark = st.text_input("Benchmark:", value="BOVA11.SA")
    with col2:
        start_d = st.date_input("Data Inicial:", value=pd.to_datetime("2024-01-01"))
        trail_length = st.slider("Tamanho da Cauda (Semanas/Pontos):", min_value=2, max_value=30, value=10)

    if st.button("Gerar Gráfico RRG"):
        tickers_list = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
        
        if not tickers_list:
            st.warning("Insira pelo menos um ativo válido.")
            return

        with st.spinner("Calculando RS-Ratio e RS-Momentum..."):
            try:
                # Instancia e roda os cálculos da classe original
                rrg = RRGCalculator(
                    tickers=tickers_list,
                    benchmark=benchmark.strip().upper(),
                    start_date=start_d.strftime('%Y-%m-%d')
                )
                
                rrg.fetch_data()
                rrg.calculate_rrg()
                
                latest_values = rrg.get_latest_values()
                trails = rrg.get_trails(length=int(trail_length))

                if not latest_values:
                    st.error("Dados insuficientes para gerar o gráfico RRG.")
                    return

                # Plotagem do Quadrante RRG
                fig, ax = plt.subplots(figsize=(10, 10))
                
                # Configura os eixos cruzados em 100 (Centro do RRG)
                ax.axhline(100, color='gray', linestyle='-', linewidth=1.2)
                ax.axvline(100, color='gray', linestyle='-', linewidth=1.2)
                
                # Identificação dos quadrantes nas pontas do gráfico
                ax.text(101, 101, "LEADING (Liderança)", color='green', fontsize=12, fontweight='bold')
                ax.text(101, 98.5, "WEAKENING (Enfraquecimento)", color='orange', fontsize=12, fontweight='bold')
                ax.text(97.5, 98.5, "LAGGING (Atraso)", color='red', fontsize=12, fontweight='bold')
                ax.text(97.5, 101, "IMPROVING (Melhoria)", color='blue', fontsize=12, fontweight='bold')

                # Desenha as caudas (trails) e os pontos atuais de cada ativo
                for ticker in tickers_list:
                    if ticker in trails and ticker in latest_values:
                        trail_df = trails[ticker]
                        # Desenha a linha de rastro (cauda)
                        ax.plot(trail_df['RS_Ratio'], trail_df['RS_Momentum'], alpha=0.5, linestyle='-', linewidth=1.5)
                        
                        # Desenha o ponto atual na ponta da cauda
                        current = latest_values[ticker]
                        ax.scatter(current['RS_Ratio'], current['RS_Momentum'], s=100, label=ticker)
                        ax.annotate(ticker, (current['RS_Ratio'] + 0.1, current['RS_Momentum'] + 0.1), fontsize=9)

                ax.set_title(f"RRG contra {benchmark.upper()}", fontsize=14, fontweight='bold')
                ax.set_xlabel("RS-Ratio")
                ax.set_ylabel("RS-Momentum")
                ax.grid(True, linestyle=':', alpha=0.6)
                
                # Ajusta limites para manter o centro visível de forma harmoniosa
                ax.set_xlim(95, 105)
                ax.set_ylim(95, 105)
                
                st.pyplot(fig)

                # Exibição de tabela com valores atuais
                st.subheader("Métricas Atuais de Rotação")
                df_metrics = pd.DataFrame(latest_values).T
                st.dataframe(df_metrics.round(2), use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao gerar o RRG: {str(e)}")