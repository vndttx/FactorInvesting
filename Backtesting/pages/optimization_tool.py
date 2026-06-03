import streamlit as st
import matplotlib.pyplot as plt

def render():
    st.header("Portfolio Optimization (Markowitz)")

    col1, col2 = st.columns(2)
    with col1:
        tickers_input = st.text_input("Tickers (separados por vírgula):", value="BBAS3.SA, ITUB4.SA, CMIG4.SA, VALE3.SA")
        start_d = st.date_input("Data de Início:", value=pd.to_datetime("2020-01-01"))
    
    with col2:
        end_d = st.date_input("Data de Fim:", value=pd.to_datetime(pd.Timestamp.now().strftime('%Y-%m-%d')))
        num_portfolios = st.number_input("Número de Simulações (Monte Carlo):", min_value=100, max_value=50000, value=5000, step=500)

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
                results, weights, max_sharpe, min_vol, balanced = optimizer.simulate_portfolios(num_simulations=num_portfolios)
                
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