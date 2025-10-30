import yfinance as yf
import pandas as pd

# Configuração do período e carteira
inicio = "2010-01-01"  # Data inicial
final = "2024-11-28"   # Data final
carteira1 = ["AURE3", "BBAS3", "BRKM5", "CSAN3", "CSNA3", "ITUB4", "SIMH3"]  # Ações na carteira
aporte_inicial = 100000  # Aporte inicial em reais (distribuído igualmente entre as ações)

# Baixando os preços ajustados e dividendos
carteira = [acao + ".SA" for acao in carteira1]
precos = yf.download(carteira, start=inicio, end=final)['Adj Close']
precos.dropna(inplace=True)

# Calculando a quantidade de ações adquiridas no início
quantidade_acoes = {}
for acao in carteira:
    preco_inicial = precos[acao].iloc[0]
    quantidade_acoes[acao] = (aporte_inicial / len(carteira)) / preco_inicial

# Calculando os dividendos recebidos por ação
dividendos_recebidos = {}
for acao in carteira:
    # Filtrar os dividendos pagos pela ação específica
    dividendos_acao = dividendos[dividendos.index.isin(precos.index)][acao]
    dividendos_recebidos[acao] = (dividendos_acao.sum() * quantidade_acoes[acao])

# Resultado final
total_dividendos = sum(dividendos_recebidos.values())
print(f"Dividendos totais recebidos no período de {inicio} a {final}: R$ {total_dividendos:.2f}")
print("\nDividendos por ação:")
for acao, total in dividendos_recebidos.items():
    print(f"- {acao}: R$ {total:.2f}")