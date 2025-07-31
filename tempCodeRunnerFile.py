import pandas as pd
import bt as bt
import yfinance as yf
import matplotlib
import datetime as dt
import numpy as np
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
from scipy.optimize import minimize
plt.style.use("dark_background")

# periodo de observacao da carteira
inicio = dt.date(1999, 1, 1)
final = dt.date(2025, 6, 30)

carteira = ['PETR4', 'VALE3', 'BBAS3', 'ITUB4', 'BBSE3', 'CMIG4', 'CSMG3', 'GOGL34', 'ABCB4', 'VBBR3', 'AAPL34', 'BPAC11']
#np.setdiff1d(carteira1, carteira2) # -> verifica a diferença entre as carteiras 1 e 2

carteira = [acao + ".SA" for acao in carteira]

precos = yf.download(carteira, inicio, final)['Close']
precos.dropna(inplace=True)

data = bt.get(carteira, start = f"{inicio:%Y-%m-%d}", end = f"{final:%Y-%m-%d}")

retornos = data.pct_change().apply(lambda x: np.log(1+x)).dropna()
media_retornos = retornos.mean()
matriz_cov = retornos.cov()


# Passo 1: Calcular os pesos otimizados
precos = data.copy()
retornos = precos.pct_change().apply(lambda x: np.log(1 + x)).dropna()
media_retornos = retornos.mean()
matriz_cov = retornos.cov()

# Configurações
numero_carteiras = 100000
tabela_retornos_esperados = np.zeros(numero_carteiras)
tabela_volatilidades_esperadas = np.zeros(numero_carteiras)
tabela_sharpe = np.zeros(numero_carteiras)
tabela_pesos = np.zeros((numero_carteiras, len(precos.columns)))

# Simulação de carteiras
for k in range(numero_carteiras):
    pesos = np.random.random(len(precos.columns))
    pesos = pesos / np.sum(pesos)
    tabela_pesos[k, :] = pesos
    
    tabela_retornos_esperados[k] = np.sum(media_retornos * pesos * 252)
    tabela_volatilidades_esperadas[k] = np.sqrt(np.dot(pesos.T, np.dot(matriz_cov * 252, pesos)))
    tabela_sharpe[k] = tabela_retornos_esperados[k] / tabela_volatilidades_esperadas[k]

# Carteira com Sharpe máximo
indice_do_sharpe_maximo = tabela_sharpe.argmax()
pesos_otimizados = tabela_pesos[indice_do_sharpe_maximo]

indice_do_sharpe_maximo = tabela_sharpe.argmax()
tabela_pesos[indice_do_sharpe_maximo]


df = pd.DataFrame(carteira, columns=['Stock'])
df['Weight'] = pd.DataFrame(tabela_pesos[indice_do_sharpe_maximo])

#print(df['Stock'])
#print(df['Weight'])

data = bt.get(carteira, start = f"{inicio:%Y-%m-%d}", end = f"{final:%Y-%m-%d}")

# Converter para dicionário (formato necessário para WeighSpecified)
ativos = precos.columns
pesos_dicionario = dict(zip(ativos, pesos_otimizados))

#estratégia rebalanceando a carteira mensalmente
Mensal = bt.Strategy('Mensal',
                       [bt.algos.RunMonthly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighSpecified(**pesos_dicionario),
                        bt.algos.Rebalance()])

#estratégia rebalanceando a carteira trimestralmente
Trimestral = bt.Strategy('Trimestral',
                       [bt.algos.RunQuarterly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighSpecified(**pesos_dicionario),
                        bt.algos.Rebalance()])

#estratégia rebalanceando a carteira anualmente
Anual = bt.Strategy('Anual', 
                   [ bt.algos.RunYearly(),
                     bt.algos.SelectAll(),
                     bt.algos.WeighSpecified(**pesos_dicionario),
                     bt.algos.Rebalance()]
                    )

#estratégia comprando a carteira apenas uma vez
BuyandHold = bt.Strategy('Buy And Hold',
                       [bt.algos.RunMonthly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighSpecified(**pesos_dicionario),
                        bt.algos.Rebalance()])

# Passo 3: Criar e rodar os backtests
st1 = bt.Backtest(Mensal, data)
st2 = bt.Backtest(Trimestral, data)
st3 = bt.Backtest(Anual, data)
st4 = bt.Backtest(BuyandHold, data)


# Rodar os backtests para as três estratégias
result = bt.run(st1, st2, st3, st4)

#comando para permitir que os gráficos sejam mostrados
plt.ioff()

# plotando a curva de rentabilidade da carteira
result.plot()
plt.show()

# estatísticas consolidadas
result.display()