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
final = dt.date(2025, 7, 29)

carteira = ['PETR4', 'VALE3', 'BBAS3', 'ITUB4', 'BBSE3', 'CMIG4', 'CSMG3', 'ABCB4', 'VBBR3', 'AAPL34', 'JBSS32']

pesos = [0.1558, 0.1392, 0.1148, 0.0996, 0.0859, 0.0819, 0.0778, 0.0663, 0.0532, 0.0475, 0.0473, 0.0308]

carteira = [acao + ".SA" for acao in carteira]

precos = yf.download(carteira, inicio, final)['Close']
precos.dropna(inplace=True)

ativos = precos.columns
pesos_dicionario = dict(zip(ativos, pesos))

strategy1 = bt.Strategy('Pesos_dados',
                       [bt.algos.RunQuarterly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighSpecified(**pesos_dicionario),
                        bt.algos.Rebalance()])

strategy2 = bt.Strategy('Pesos_iguais', 
                   [ bt.algos.RunQuarterly(),
                     bt.algos.SelectAll(),
                     bt.algos.WeighEqually(),
                     bt.algos.Rebalance()]
                    )

st1 = bt.Backtest(strategy1, precos)
st2 = bt.Backtest(strategy2, precos)

result = bt.run(st1, st2)

plt.ioff()

result.plot()

plt.show()

result.display()