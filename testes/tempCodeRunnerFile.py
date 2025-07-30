import numpy as np
import pandas as pd
import yfinance as yf

carteira = ["SPYI11", "ABCB4", "ITUB4", "VALE3"]

periodo = "10y"

carteira = [acao + ".SA" for acao in carteira]

df = yf.download(carteira, period = periodo, actions=True)

df.dropna(inplace=True)

print (df)

quantidade1 = [10000/acao for acao in df]

print(quantidade1)