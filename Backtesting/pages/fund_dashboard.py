import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import fund_tool

st.set_page_config(page_title="Dashboard de Fundos", layout="wide")
st.title("🏦 Dashboard de Análise de Fundos")

st.sidebar.header("Seleção de Ativos")
fund_cnpj = st.sidebar.text_input("CNPJ do Fundo (Apenas números):", value="")
bench_cnpj = st.sidebar.text_input("CNPJ do Benchmark (Opcional):", value="")

if st.sidebar.button("Analisar Fundo"):
    if not fund_cnpj:
        st.error("Por favor, insira o CNPJ do Fundo.")
    else:
        with st.spinner("Buscando dados e processando retornos..."):
            try:
                df, meta = fund_tool.get_fund_data_and_compare(fund_cnpj, bench_cnpj if bench_cnpj else None)
                
                st.subheader(f"Fundo: {meta.get('name', 'Não identificado')}")
                st.info(f"**Data de Início:** {meta.get('start_date').strftime('%Y-%m-%d') if meta.get('start_date') else 'N/A'}")
                
                total_return = (df.iloc[-1] / 100 - 1) * 100
                
                st.write("### Retorno Total Acumulado")
                cols = st.columns(len(df.columns))
                for idx, col_name in enumerate(df.columns):
                    cols[idx].metric(label=f"Retorno {col_name}", value=f"{total_return[col_name]:.2f}%")
                
                fig, ax = plt.subplots(figsize=(12, 5))
                for col in df.columns:
                    linewidth = 2.5 if col == 'Fund' else 1.5
                    alpha = 1.0 if col == 'Fund' else 0.7
                    ax.plot(df.index, df[col], label=col, linewidth=linewidth, alpha=alpha)
                
                ax.set_title("Comparativo de Performance (Base 100)")
                ax.grid(True, linestyle='--', alpha=0.3)
                ax.legend()
                
                st.pyplot(fig)
                
            except Exception as e:
                st.error(f"Erro ao processar análise do fundo: {str(e)}")