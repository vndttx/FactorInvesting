import bt
import matplotlib.pyplot as plt
import pandas as pd

data = bt.get('VALE3.SA', start='1999-01-01')

#data.rolling() pega os ultimos X periodos e .mean() faz a média
sma = data.rolling(50).mean()

#plot = bt.merge(data, sma).plot(figsize=(15, 5))
#so tirar o comentario se quiser plotar

class SelectWhere(bt.Algo):
    def __init__(self, signal):
        self.signal = signal
    def __call__(self, target):
        
        if target.now in self.signal.index:
            sig = self.signal.loc[target.now]

            selected = list(sig.index[sig])

            target.temp['selected'] = selected

        return True

signal = data > sma

s = bt.Strategy('MM50', [SelectWhere(data > sma),
                               bt.algos.WeighEqually(),
                               bt.algos.Rebalance()])

plt.ioff()

t = bt.Backtest(s, data)
res = bt.run(t)
res.plot()
plt.show()

#res.display() estatisticas dos trades


