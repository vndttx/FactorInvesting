
import pandas as pd
import requests

def get_tickers():
    url = "https://www.fundamentus.com.br/resultado.php"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        print("Fetching Fundamentus...")
        # read_html needs lxml or html5lib. Requests is safer for headers.
        r = requests.get(url, headers=headers)
        df_list = pd.read_html(r.text, decimal=',', thousands='.')
        
        if len(df_list) > 0:
            df = df_list[0]
            print(f"Columns: {df.columns}")
            tickers = df['Papel'].tolist()
            print(f"Found {len(tickers)} tickers.")
            print(f"Sample: {tickers[:10]}")
            return tickers
        else:
            print("No tables found.")
            return []
            
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    t = get_tickers()
