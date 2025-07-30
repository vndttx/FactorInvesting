import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np

pd.options.mode.chained_assignment = None

ativo = 'AGRO3.SA'
dados_ativo = yf.download(ativo)
dados_ativo['Close'].plot()
dados_ativo['retornos'] = dados_ativo['Close'].pct_change().dropna() 

print(dados_ativo)