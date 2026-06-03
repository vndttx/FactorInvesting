import streamlit as st
import os

st.set_page_config(
    page_title="Plataforma de Backtesting",
    page_icon="📈",
    layout="wide"
)

st.title("Welcome to the Backtesting & Analytics Platform")
st.markdown("""
Esta plataforma reúne ferramentas avançadas de análise quantitativa e finanças.
Utilize o menu ao lado para navegar entre as ferramentas disponíveis:
* **Financial Dashboard**: Análise detalhada de ativos.
* **Fund Dashboard**: Comparativo e métricas de fundos.
* **Market Breadth**: Indicadores de saúde do mercado.
* **RRG Tool**: Gráficos de Rotação Relativa.
""")