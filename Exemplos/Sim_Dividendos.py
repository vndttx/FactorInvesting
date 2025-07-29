import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

inicio = "1999-01-01"
today = datetime.now()
fim = today - pd.tseries.offsets.BusinessDay(3)
fim = fim.strftime("%Y-%m-%d")
carteira1 = ["ABCB4", "BBAS3", "ITUB4", "VALE3"]  
aporte_inicial = 100000

carteira = [acao + ".SA" for acao in carteira1]
precos = yf.download(carteira, start=inicio, end=fim)['Close']
precos.dropna(inplace=True)

quantidade_acoes = {}
for acao in carteira:
    preco_inicial = precos[acao].iloc[0]
    quantidade_acoes[acao] = (aporte_inicial / len(carteira)) / preco_inicial


#achar uma forma de colocar os dividendos pagos pelas empresas aqui    
dividendos_recebidos = {}
for acao in carteira:
    # Filtrar os dividendos pagos pela ação específica
    dividendos_acao = dividendos[dividendos.index.isin(precos.index)][acao]
    dividendos_recebidos[acao] = (dividendos_acao.sum() * quantidade_acoes[acao])
    
total_dividendos = sum(dividendos_recebidos.values())
print(f"Dividendos totais recebidos no período de {inicio} a {final}: R$ {total_dividendos:.2f}")
print("\nDividendos por ação:")
for acao, total in dividendos_recebidos.items():
    print(f"- {acao}: R$ {total:.2f}")