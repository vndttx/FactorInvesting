
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


inicio = dt.date(2010, 1, 1)
final = dt.date(2025, 5, 30)

carteira = ["VALE3", "ABCB4", "ITUB4", "BBAS3", "BBSE3", "CMIG4", "PETR4", 'CSMG3', 'VBBR3']
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
numero_carteiras = 10
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

data = bt.get(carteira, start = f"{inicio:%Y-%m-%d}", end = f"{final:%Y-%m-%d}")

# Converter para dicionário (formato necessário para WeighSpecified)
ativos = precos.columns
pesos_dicionario = dict(zip(ativos, pesos_otimizados))

#estratégia rebalanceando a carteira mensalmente
strategy1 = bt.Strategy('Rebalanceando',
                       [bt.algos.RunMonthly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighSpecified(**pesos_dicionario),
                        bt.algos.Rebalance()])
#estratégia comprando a carteira apenas uma vez
strategy2 = bt.Strategy('BuyHold', 
                   [ bt.algos.RunOnce(),
                     bt.algos.SelectAll(),
                     bt.algos.WeighSpecified(**pesos_dicionario),
                     bt.algos.Rebalance()]
                    )
#com pesos iguais
strategy3 = bt.Strategy('RB Equal',
                       [bt.algos.RunMonthly(),
                        bt.algos.SelectAll(),
                        bt.algos.WeighEqually(),
                        bt.algos.Rebalance()])

strategy4 = bt.Strategy('BH Equal', 
                   [ bt.algos.RunOnce(),
                     bt.algos.SelectAll(),
                     bt.algos.WeighEqually(),
                     bt.algos.Rebalance()]
                    )


# Passo 3: Criar e rodar os backtests
st1 = bt.Backtest(strategy1, data)
st2 = bt.Backtest(strategy2, data)
st3 = bt.Backtest(strategy3, data)
st4 = bt.Backtest(strategy4, data)

# Rodar os backtests para as três estratégias
result = bt.run(st1, st2, st3, st4)


#comando para permitir que os gráficos sejam mostrados

plt.ioff()

# plotando a curva de rentabilidade da carteira
result.plot()

plt.show()


# estatísticas consolidadas
result.display()

tabela_retornos_esperados_arit = np.exp(tabela_retornos_esperados) - 1
eixo_y_fronteira_eficiente = np.linspace(tabela_retornos_esperados_arit.min(),
tabela_retornos_esperados_arit.max(), 50)

def pegando_retorno(peso_teste):
    peso_teste = np.array(peso_teste)
    retorno = np.sum(media_retornos * peso_teste) * 252
    retorno = np.exp(retorno) - 1

    return retorno

def checando_soma_pesos(peso_teste):

    return np.sum(peso_teste)-1

def pegando_vol(peso_teste):
    peso_teste = np.array(peso_teste)
    vol = np.sqrt(np.dot(peso_teste.T, np.dot(matriz_cov*252, peso_teste)))
    
    return vol

peso_inicial = [1/len(carteira)] * len(carteira) 
limites = tuple([(0, 1) for ativo in carteira])

eixo_x_fronteira_eficiente = []

for retorno_possivel in eixo_y_fronteira_eficiente:
    
    restricoes = ({'type':'eq', 'fun':checando_soma_pesos},
            {'type':'eq', 'fun': lambda w: pegando_retorno(w) - retorno_possivel})
    
    result = minimize(pegando_vol,peso_inicial,method='SLSQP', bounds=limites, 
                      constraints=restricoes)
    eixo_x_fronteira_eficiente.append(result['fun'])
fig, ax = plt.subplots()

ax.scatter(tabela_volatilidades_esperadas, tabela_retornos_esperados_arit, c = tabela_sharpe)
plt.xlabel("Volatilidade esperada")
plt.ylabel("Retorno esperado")
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.scatter(tabela_volatilidades_esperadas[indice_do_sharpe_maximo], 
            tabela_retornos_esperados_arit[indice_do_sharpe_maximo], c = "red")
ax.plot(eixo_x_fronteira_eficiente, eixo_y_fronteira_eficiente)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')

plt.show()