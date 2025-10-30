
import yfinance as yf
import matplotlib.pyplot as plt
import datetime as dt
from datetime import datetime, timedelta
import matplotlib.ticker as mtick
import matplotlib.dates as mdate

final = datetime.now()
inicio = final - dt.timedelta(days = 3650)

ativo = "VALE3.SA"

precos = yf.download(ativo, inicio, final)['Close']

precos_max = precos.cummax()
drawdowns = precos/precos_max - 1
drawdown_maximo = drawdowns.min()
print(drawdown_maximo)

fig, ax = plt.subplots()

ax.plot(drawdowns.index, drawdowns)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.xaxis.set_major_locator(mdate.YearLocator(1))
plt.show()