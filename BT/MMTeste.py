import bt
import matplotlib.pyplot as plt
import pandas as pd

inicio = '1995-01-01'
tickers = ['VALE3.SA', 'PETR4.SA', 'BBAS3.SA']
##com itub4 fica pior
##melhor com vale3, petr4 e bbas3 usando a mm21

try:
    data = bt.get(tickers, start=inicio)
except Exception as e:
    print(f"Erro ao obter dados: {e}")
    exit()
  
def above_sma(data, sma_per = 21, name='above_sma'):
    
        signal = data > data.rolling(sma_per).mean()

        s = bt.Strategy(name, [
            bt.algos.SelectWhere(signal),
            bt.algos.WeighEqually(),
            bt.algos.Rebalance()
        ])
        return bt.Backtest(s, data)
        
def bhBenchmark(data, name='bhBenchmark'):
        
        s2 = bt.Strategy(name, [
            bt.algos.RunOnce(),
            bt.algos.SelectAll(),
            bt.algos.WeighEqually(),
            bt.algos.Rebalance()
        ])        
        return bt.Backtest(s2, data)
    
mm9 = above_sma(data, sma_per = 9, name ='mm9')
mm21 = above_sma(data, sma_per = 21, name ='mm21')
mm200 = above_sma(data, sma_per = 200, name ='mm200')
    
benchmark = bhBenchmark(data, name='benchmark')
    
plt.ioff()
    
res = bt.run(mm9, mm21, mm200, benchmark)
res.plot(freq='ME')
    
plt.show()

#print(res.stats) -> alternativa ao res.display(), tabela

res.display() #estatisticas dos trades

