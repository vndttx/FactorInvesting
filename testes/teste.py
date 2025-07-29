import numpy as np
import pandas as pd
import yfinance as yf

carteira = ["SPYI11", "ABCB4", "ITUB4", "VALE3"]

periodo = "10y"

carteira = [acao + ".SA" for acao in carteira]

df = yf.download(carteira, period = periodo, actions=True)

df.dropna(inplace=True)

print (df)

somaDiv = df['Dividends'].sum()

print(f"Total dividend income in the last {periodo}: {somaDiv}")