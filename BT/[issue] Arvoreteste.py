import bt
import matplotlib.pyplot as plt
import pandas as pd

def ma_cross(ticker, start='1999-01-01', short_ma=21, long_ma=144, name='ma_cross'):
    data = bt.get(ticker, start=start)
    short_sma = data.rolling(short_ma).mean()
    long_sma  = data.rolling(long_ma).mean()

    tw = long_sma.copy()
    tw[short_sma > long_sma] = 1.0
    tw[short_sma <= long_sma] = -1.0
    tw[long_sma.isnull()] = 0.0


    s = bt.Strategy(name, [
        bt.algos.WeighTarget(tw),
        bt.algos.Rebalance()
        ], [ticker])

    return bt.Backtest(s, data)

t1 = ma_cross('BBAS3.SA', name='BBAS3_cruzamento')
t2 = ma_cross('VALE3.SA', name='vale3_cruzamento')

res = bt.run(t1, t2)


data = bt.merge(res['BBAS3_cruzamento'].prices, res['vale3_cruzamento'].prices)


s = bt.Strategy('s', [bt.algos.SelectAll(),
                      bt.algos.WeighInvVol(),
                      bt.algos.Rebalance()])


t = bt.Backtest(s, data)
res = bt.run(t)
plt.ioff()
res.plot()
plt.show()