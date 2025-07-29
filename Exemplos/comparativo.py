import pandas as pd
import bt as bt
import yfinance as yf
import matplotlib
import datetime as dt
import numpy as np
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
from scipy.optimize import minimize
plt.style.use("dark_background")


inicio = dt.date(2010, 1, 1)
final = dt.date(2025, 5, 30)

carteira = ["VALE3", "PETR4"]
#np.setdiff1d(carteira1, carteira2) # -> verifica a diferença entre as carteiras 1 e 2

carteira = [acao + ".SA" for acao in carteira]

precos = yf.download(carteira, inicio, final)['Close']
precos.dropna(inplace=True)

#data = bt.get(carteira, start = f"{inicio:%Y-%m-%d}", end = f"{final:%Y-%m-%d}")

#data["retorno"] = data["Close"].pct_change()

print(precos)