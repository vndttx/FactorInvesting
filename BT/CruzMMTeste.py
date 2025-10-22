import bt
import matplotlib.pyplot as plt
import pandas as pd

inicio = '1999-01-01'
tickers = ['PETR4.SA']

try:
    data = bt.get(tickers, start=inicio)
except Exception as e:
    print(f"Erro ao obter dados: {e}")
    exit()
    

mediacurta = data.rolling(9).mean()
mediamedia = data.rolling(21).mean()
medialonga = data.rolling(80).mean()

tw = mediamedia.copy()
condicao_compra = (mediacurta >= mediamedia) & (medialonga <= mediamedia)
tw[condicao_compra] = 1.0
condicao_venda = (medialonga > mediamedia) & (mediacurta < mediamedia)
tw[condicao_venda] = -1.0
tw[mediamedia.isnull()] = 0.0

s_mm_crossover = bt.Strategy('MM Crossover', [
    bt.algos.WeighTarget(tw),
    bt.algos.Rebalance()
])

s_benchmark = bt.Strategy('Benchmark', [
    bt.algos.RunOnce(),
    bt.algos.SelectAll(),
    bt.algos.WeighEqually(),
    bt.algos.Rebalance()
])

res = bt.run(bt.Backtest(s_mm_crossover, data), bt.Backtest(s_benchmark, data))

res.plot(freq='ME', figsize=(15, 5))
plt.title('Desempenho da Estratégia de Média Móvel vs. Benchmark')

plt.show()

ma_cross = bt.Strategy('ma_cross', [
    bt.algos.WeighTarget(tw),
    bt.algos.Rebalance()
    ])

t = bt.Backtest(ma_cross, data)
res = bt.run(t)

res.plot()
plt.show()
