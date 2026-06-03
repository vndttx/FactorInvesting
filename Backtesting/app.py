import streamlit as nn
import os

nn.set_page_config(page_title="Dashboard Financeiro", layout="wide")

import financial_dashboard
import fund_dashboard
import market_breadth
import rrg_tool

paginas = {
    "Dashboard Financeiro": financial_dashboard,
    "Dashboard de Fundos": fund_dashboard,
    "Market Breadth": market_breadth,
    "RRG Tool": rrg_tool
}

opcao = nn.sidebar.selectbox("Selecione a Ferramenta", list(paginas.keys()))

nn.title(opcao)
paginas[opcao].render()