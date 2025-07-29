import requests
import pandas as pd

#selic = 432
#ipca = 433
#PTAX (dólar) = 1

codigo = 432

url_banco_central = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json'

dados_selic = requests.get(url_banco_central)

json_selic = dados_selic.json()

df = pd.DataFrame(json_selic)

df['data'] = pd.to_datetime(df['data'], format = '%d/%m/%Y')

df = df.set_index('data')

df['valor'] = df['valor'].astype(float)

df = df.resample("M").last() #reorganizando os dados para outra periodicidade

df

print(df)

df.plot()

