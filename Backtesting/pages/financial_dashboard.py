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
    valuation.render()
    
with tab_back:
    backtest_tool.render()
    
with tab_opt:
    optimization_tool.render()
    
with tab_breadth:
    market_breadth.render()

with tab_rrg:
    rrg_tool.render()
