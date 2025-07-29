import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np

pd.options.mode.chained_assignment = None

ativo = 'AGRO3.SA'
dados_ativo = yf.download(ativo)
dados_ativo['Close'].plot()
dados_ativo['retornos'] = dados_ativo['Close'].pct_change().dropna() 

retorno = 2

filtrando_retorno = lambda x: x if x > 0 else 0

filtrando_retorno(retorno)

dados_ativo['retornos_postivos'] = dados_ativo['retornos'].apply(lambda x: x if x > 0 else 0)
dados_ativo['retornos_negativos'] = dados_ativo['retornos'].apply(lambda x: abs(x) if x < 0 else 0)

dados_ativo['media_retornos_positivos'] = dados_ativo['retornos_postivos'].rolling(window = 22).mean()
dados_ativo['media_retornos_negativos'] = dados_ativo['retornos_negativos'].rolling(window = 22).mean()

dados_ativo = dados_ativo.dropna()

dados_ativo['RSI'] = (100 - 100/(1 + dados_ativo['media_retornos_positivos']/dados_ativo['media_retornos_negativos']))

dados_ativo.loc[dados_ativo['RSI'] < 30, 'compra'] = 'sim'
dados_ativo.loc[dados_ativo['RSI'] > 30, 'compra'] = 'nao'

datas_compra = []
datas_venda = []

for i in range(len(dados_ativo)):
    print(i)
    
    if "sim" in dados_ativo['compra'].iloc[i]:
        
        datas_compra.append(dados_ativo.iloc[i+1].name)
        
print(datas_compra)

data_compra = []
data_venda = []

for i in range(len(dados_ativo)):
    
    if "sim" in dados_ativo['compra'].iloc[i]:
        
        data_compra.append(dados_ativo.iloc[i+1].name)
        
        for j in range(1, 11):
            
            if dados_ativo['RSI'].iloc[i + j] > 40: #vendo se nos proximos 10 dias o RSI passa de 40
                
                data_venda.append(dados_ativo.iloc[i + j + 1].name) #vende no dia seguinte q bater 40
                break
                
            elif j == 10:
                data_venda.append(dados_ativo.iloc[i + j + 1].name)
print(data_venda)