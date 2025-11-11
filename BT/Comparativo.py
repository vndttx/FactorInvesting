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

inicio = dt.date(1999, 1, 1)
final = dt.date(2025, 9, 19)

carteira1 = ['PETR4', 'VALE3', 'BBAS3', 'ITUB4']
carteira2 = ['BOVA11', 'LFTS11']
#carteira2 = ['DIVO11', 'IVVB11', 'IMAB11', 'GOLD11']

#np.setdiff1d(carteira1, carteira2) # -> verifica a diferença entre as carteiras 1 e 2

carteira1 = [acao + ".SA" for acao in carteira1]

precos = yf.download(carteira1, inicio, final)['Close']
precos.dropna(inplace=True)
data = bt.get(carteira1, start = f"{inicio:%Y-%m-%d}", end = f"{final:%Y-%m-%d}")

Carteira1 = bt.Strategy('Carteira1',
                       [bt.algos.RunQuarterly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighEqually(),
                        bt.algos.Rebalance()])

st1 = bt.Backtest(Carteira1, data)

carteira2 = [acao + ".SA" for acao in carteira2]

precos2 = yf.download(carteira2, inicio, final)['Close']
precos2.dropna(inplace=True)
data2 = bt.get(carteira2, start = f"{inicio:%Y-%m-%d}", end = f"{final:%Y-%m-%d}")


Carteira2 = bt.Strategy('Carteira2',
                       [bt.algos.RunQuarterly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighEqually(),
                        bt.algos.Rebalance()])

st2 = bt.Backtest(Carteira2, data2)

result = bt.run(st1, st2)

plt.ioff()

result.plot()
plt.show()

result.display()