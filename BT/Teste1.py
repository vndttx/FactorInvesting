import bt
import matplotlib.pyplot as plt


data = bt.get('PETR4.SA, VALE3.SA', start='1999-01-01')

s = bt.Strategy('s1', [bt.algos.RunMonthly(),
                       bt.algos.SelectAll(),
                       bt.algos.WeighEqually(),
                       bt.algos.Rebalance()])

test = bt.Backtest(s, data)
res = bt.run(test)

s2 = bt.Strategy('s2', [bt.algos.RunMonthly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighInvVol(),
                        bt.algos.Rebalance()])


test2 = bt.Backtest(s2, data)

res2 = bt.run(test, test2)

plt.ioff()
res2.plot()
plt.show()
res2.display()



