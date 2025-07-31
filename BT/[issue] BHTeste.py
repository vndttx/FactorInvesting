import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import ffn
import bt

names = ['VALE3.SA','PETR4.SA','CDI']
dates = pd.date_range(start='1999-01-01',end='2025-07-30', freq=pd.tseries.offsets.BDay())
n = len(dates)
rdf = pd.DataFrame(
    np.zeros((n, len(names))),
    index = dates,
    columns = names
)

np.random.seed(1)
rdf['VALE3.SA'] = np.random.normal(loc = 0.1/n,scale=0.2/np.sqrt(n),size=n)
rdf['PETR4.SA'] = np.random.normal(loc = 0.04/n,scale=0.05/np.sqrt(n),size=n)
rdf['CDI'] = 0.

pdf = 100*np.cumprod(1+rdf)

plt.ioff()
pdf.plot()
plt.show()