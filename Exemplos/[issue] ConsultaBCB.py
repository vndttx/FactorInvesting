import requests
import pandas as pd
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
plt.style.use("dark_background")

idSelic = 432
idIpca = 433
idPTAX = 1

dataInicial = "29/06/2016"
dataFinal = "29/06/2025"

url_banco_central = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{idSelic}/dados?formato=json&dataInicial={dataInicial}&dataFinal={dataFinal}'

dados_selic = requests.get(url_banco_central)

json_selic = dados_selic.json()

df = pd.DataFrame(json_selic)

df['data'] = pd.to_datetime(df['data'], format = '%d/%m/%Y')

df = df.set_index('data')

df['valor'] = df['valor'].astype(float)

df = df.resample("ME").last() #reorganizando os dados para outra periodicidade

print(df)

df.plot()

plt.show()

