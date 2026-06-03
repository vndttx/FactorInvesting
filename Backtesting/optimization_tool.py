import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime

class PortfolioOptimizer:
    def __init__(self, tickers, start_date, end_date=None, risk_free_rate=0.10, price_data=None):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date if end_date else pd.Timestamp.now().strftime('%Y-%m-%d')
        self.risk_free_rate = risk_free_rate
        self.price_data_input = price_data
        self.data = pd.DataFrame()
        self.returns = pd.DataFrame()
        self.mean_returns = None
        self.cov_matrix = None

    def fetch_data(self):
        if self.price_data_input is not None:
            if isinstance(self.price_data_input, pd.DataFrame) and 'Close' in self.price_data_input.columns:
                data = self.price_data_input['Close']
            else:
                data = self.price_data_input
        else:
            data = yf.download(self.tickers, start=self.start_date, end=self.end_date)['Close']
        
        if isinstance(data, pd.Series):
            data = data.to_frame(name=self.tickers[0])

        us_stocks = [t for t in self.tickers if not t.endswith('.SA') and not 'BRL' in t and not '=' in t]
        
        if us_stocks:
            currency_data = yf.download("USDBRL=X", start=self.start_date, end=self.end_date)['Close']
            if isinstance(currency_data, pd.DataFrame): 
                currency_data = currency_data.iloc[:, 0]
            currency_data = currency_data.reindex(data.index).ffill().bfill()
            
            for ticker in us_stocks:
                if ticker in data.columns:
                    data[ticker] = data[ticker] * currency_data
                    
        self.data = data.ffill().bfill().dropna()
        self.returns = self.data.pct_change().dropna()
        self.mean_returns = self.returns.mean() * 252
        self.cov_matrix = self.returns.cov() * 252

    def optimize(self, num_portfolios=5000):
        if self.data.empty:
            self.fetch_data()
            
        np.random.seed(42)
        num_assets = len(self.tickers)
        weights_record = np.random.random((num_portfolios, num_assets))
        weights_record = (weights_record.T / weights_record.sum(axis=1)).T

        p_returns = np.dot(weights_record, self.mean_returns)
        p_volatility = np.sqrt(np.einsum('ij,jk,ik->i', weights_record, self.cov_matrix, weights_record))
        p_sharpe = (p_returns - self.risk_free_rate) / p_volatility
        
        results = np.array([p_returns, p_volatility, p_sharpe])
        
        def calc_metrics(w):
            port_ret = self.returns.dot(w)
            wealth_index = (1 + port_ret).cumprod()
            peak = wealth_index.cummax()
            max_dd = ((wealth_index - peak) / peak).min()
            equity_curve = 100 * wealth_index
            return max_dd, equity_curve

        max_sharpe_idx = np.argmax(results[2])
        min_vol_idx = np.argmin(results[1])
        
        rets, vols = results[0], results[1]
        norm_ret = (rets - rets.min()) / (rets.max() - rets.min())
        norm_vol = (vols - vols.min()) / (vols.max() - vols.min())
        distances = np.sqrt((norm_ret - 1)**2 + (norm_vol - 0)**2)
        optimal_idx = np.argmin(distances)
        
        w_sharpe = weights_record[max_sharpe_idx]
        w_vol = weights_record[min_vol_idx]
        w_opt = weights_record[optimal_idx]
        
        dd_sharpe, curve_sharpe = calc_metrics(w_sharpe)
        dd_vol, curve_vol = calc_metrics(w_vol)
        dd_opt, curve_opt = calc_metrics(w_opt)
        
        max_sharpe_port = {
            'Return': results[0, max_sharpe_idx],
            'Volatility': results[1, max_sharpe_idx],
            'Sharpe': results[2, max_sharpe_idx],
            'MaxDrawdown': dd_sharpe,
            'Weights': dict(zip(self.tickers, w_sharpe)),
            'EquityCurve': curve_sharpe
        }
        
        min_vol_port = {
            'Return': results[0, min_vol_idx],
            'Volatility': results[1, min_vol_idx],
            'Sharpe': results[2, min_vol_idx],
            'MaxDrawdown': dd_vol,
            'Weights': dict(zip(self.tickers, w_vol)),
            'EquityCurve': curve_vol
        }
        
        optimal_port = {
            'Return': results[0, optimal_idx],
            'Volatility': results[1, optimal_idx],
            'Sharpe': results[2, optimal_idx],
            'MaxDrawdown': dd_opt,
            'Weights': dict(zip(self.tickers, w_opt)),
            'EquityCurve': curve_opt
        }
        
        return results, max_sharpe_port, min_vol_port, optimal_port
def render():
        st.header("Portfolio Optimization (Markowitz)")

        col1, col2 = st.columns(2)
        with col1:
            tickers_input = st.text_input("Tickers (separados por vírgula):", value="BBAS3.SA, ITUB4.SA, CMIG4.SA, VALE3.SA", key="opt_tickers")
            start_d = st.date_input("Data de Início:", value=datetime(2020, 1, 1), key="opt_start_date")
        
        with col2:
            end_d = st.date_input("Data de Fim:", value=datetime.now(), key="opt_end_date")
            num_portfolios = st.number_input("Número de Simulações (Monte Carlo):", min_value=100, max_value=50000, value=5000, step=500, key="opt_num_portfolios")

        if st.button("Otimizar Carteira"):
            tickers_list = [t.strip().upper() for t in tickers_input.split(",")]
            
            with st.spinner("Descarregando dados e simulando portfólios..."):
                try:
                    optimizer = PortfolioOptimizer(
                        tickers=tickers_list,
                        start_date=start_d.strftime('%Y-%m-%d'),
                        end_date=end_d.strftime('%Y-%m-%d')
                    )
                    
                    optimizer.fetch_data()
                    results, max_sharpe, min_vol, balanced = optimizer.optimize(num_portfolios=num_portfolios)
                    
                    if max_sharpe is None:
                        st.error("Não foi possível gerar a otimização com os dados atuais.")
                        return

                    # Exibição dos resultados das três carteiras otimizadas
                    st.subheader("Resultados das Carteiras Otimizadas")
                    c1, c2, c3 = st.columns(3)
                    
                    with c1:
                        st.markdown("### 🎯 Máximo Sharpe")
                        st.metric("Retorno Anual", f"{max_sharpe['Return']*100:.2f}%")
                        st.metric("Volatilidade", f"{max_sharpe['Volatility']*100:.2f}%")
                        st.metric("Sharpe Ratio", f"{max_sharpe['Sharpe']:.2f}")
                        st.metric("Max Drawdown", f"{max_sharpe['MaxDrawdown']*100:.2f}%")
                        
                    with c2:
                        st.markdown("### 🛡️ Mínima Volatilidade")
                        st.metric("Retorno Anual", f"{min_vol['Return']*100:.2f}%")
                        st.metric("Volatilidade", f"{min_vol['Volatility']*100:.2f}%")
                        st.metric("Sharpe Ratio", f"{min_vol['Sharpe']:.2f}")
                        st.metric("Max Drawdown", f"{min_vol['MaxDrawdown']*100:.2f}%")
                        
                    with c3:
                        st.markdown("### ⚖️ Carteira Equilibrada")
                        st.metric("Retorno Anual", f"{balanced['Return']*100:.2f}%")
                        st.metric("Volatilidade", f"{balanced['Volatility']*100:.2f}%")
                        st.metric("Sharpe Ratio", f"{balanced['Sharpe']:.2f}")
                        st.metric("Max Drawdown", f"{balanced['MaxDrawdown']*100:.2f}%")

                    # Pesos de cada ativo por estratégia
                    st.subheader("Alocação de Ativos (%)")
                    df_weights = pd.DataFrame({
                        'Máximo Sharpe': pd.Series(max_sharpe['Weights']) * 100,
                        'Mínima Volatilidade': pd.Series(min_vol['Weights']) * 100,
                        'Equilibrada': pd.Series(balanced['Weights']) * 100
                    })
                    st.dataframe(df_weights.round(2), use_container_width=True)

                    # Gráfico da Fronteira Eficiente
                    st.subheader("Gráfico da Fronteira Eficiente")
                    fig, ax = plt.subplots(figsize=(10, 6))
                    sc = ax.scatter(results[1, :], results[0, :], c=results[2, :], cmap='viridis', marker='o', s=10, alpha=0.3)
                    fig.colorbar(sc, label='Sharpe Ratio', ax=ax)
                    
                    ax.scatter(max_sharpe['Volatility'], max_sharpe['Return'], color='red', marker='*', s=200, label='Max Sharpe')
                    ax.scatter(min_vol['Volatility'], min_vol['Return'], color='blue', marker='*', s=200, label='Min Volatility')
                    ax.scatter(balanced['Volatility'], balanced['Return'], color='green', marker='*', s=200, label='Balanced')
                    
                    ax.set_title("Fronteira Eficiente de Markowitz")
                    ax.set_xlabel("Volatilidade Anualizada")
                    ax.set_ylabel("Retorno Anualizado")
                    ax.legend()
                    ax.grid(True, linestyle='--', alpha=0.5)
                    st.pyplot(fig)

                    # Gráfico de Evolução Patrimonial
                    st.subheader("Evolução Patrimonial das Estratégias")
                    fig_curve, ax_curve = plt.subplots(figsize=(10, 5))
                    ax_curve.plot(max_sharpe['EquityCurve'], label='Max Sharpe', color='red')
                    ax_curve.plot(min_vol['EquityCurve'], label='Min Volatility', color='blue')
                    ax_curve.plot(balanced['EquityCurve'], label='Balanced', color='green')
                    ax_curve.set_title("Curva de Equidade Histórica (Base 1)")
                    ax_curve.set_xlabel("Data")
                    ax_curve.set_ylabel("Valor")
                    ax_curve.legend()
                    ax_curve.grid(True, linestyle='--', alpha=0.5)
                    st.pyplot(fig_curve)

                except Exception as e:
                    st.error(f"Erro ao executar a otimização: {str(e)}")