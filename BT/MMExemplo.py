import bt
import matplotlib.pyplot as plt
import pandas as pd

inicio = '1999-01-01'
ticker = 'VALE3.SA'

try:
    data = bt.get(ticker, start=inicio)
except Exception as e:
    print(f"Erro ao obter dados: {e}")
    exit()

sma = data.rolling(33).mean()
#data.rolling() pega os ultimos X periodos e .mean() faz a média

#plot = bt.merge(data, sma).plot(figsize=(15, 5))
#so tirar o comentario se quiser plotar

signal = data > sma

s = bt.Strategy('MM33', [
    bt.algos.SelectWhere(signal),
    bt.algos.WeighEqually(),
    bt.algos.Rebalance()
    ])

plt.ioff()

t = bt.Backtest(s, data)
res = bt.run(t)
res.plot()
plt.title(f'Backtest da Estratégia de Média Móvel 33 para {ticker}')
plt.show()

res.display() #estatisticas do modelo