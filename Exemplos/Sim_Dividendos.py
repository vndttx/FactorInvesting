import yfinance as yf
import numpy as np
import pandas as pd
#from datetime import datetime, timedelta


#inicio = "1999-01-01"
#today = datetime.now()
#fim = today - pd.tseries.offsets.BusinessDay(3)
#fim = fim.strftime("%Y-%m-%d")#!
#precos = yf.download(carteira, start=inicio, end=fim)['Close']

carteira = ["ABCB4", "BBAS3", "ITUB4", "VALE3", "SPYI11"]
janela = "10y"
aporte_inicial = 100000

carteira = [acao + ".SA" for acao in carteira]
dados = yf.download(carteira, period = janela, actions = True)
dados.dropna(inplace=True)

somaDiv = dados['Dividends'].sum()

for acao in carteira:
    vlrPorAcao = (aporte_inicial/len(carteira))
    print(f"{acao} = {vlrPorAcao}")

qtdAcoes = vlrPorAcao/dados['Close']

# até aqui ok ^
# achar um jeito de olhar janelas trimestrais e multiplicar os dividendos pelo total de ações naquele momento


print(f"Dividendos totais recebidos em {janela}: R$ {total_dividendos:.2f}")
print("\nDividendos por ação:")
for acao, total in dividendos_totais.items():
    print(f"- {acao}: R$ {total:.2f}")