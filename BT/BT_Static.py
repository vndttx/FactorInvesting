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

inicio = dt.date(2025, 1, 2)
final = dt.date(2025, 10, 31)

##python -m venv .venv
##source .venv/bin/activate

carteira = ['BBSE3', 'VALE3', 'PETR4', 'ITUB4', 'ABCB4', 'CMIG4', 'BBAS3', 'CSMG3', 'BRKM5', 'PRIO3', 'AGRO3']

pesos = [0.1, 0.1, 0.1, 0.1, 0.1, 0.09, 0.08, 0.08, 0.08, 0.09, 0.08]

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