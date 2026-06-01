import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


IBOV_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "AXIA3.SA", "RENT3.SA",
    "WEGE3.SA", "BPAC11.SA", "ITSA4.SA", "SUZB3.SA", "HAPV3.SA", "RADL3.SA", "RDOR3.SA", "EQTL3.SA", "PRIO3.SA", "RAIL3.SA", "LREN3.SA", "B3SA3.SA", "GGBR4.SA", "VIVT3.SA", "UGPA3.SA", "CSAN3.SA",
    "BBSE3.SA", "ASAI3.SA", "SBSP3.SA", "CMIG4.SA", "VBBR3.SA", "HYPE3.SA", "CPLE3.SA","TOTS3.SA",
    "EMBJ3.SA", "MULT3.SA", "TIMS3.SA", "PETR3.SA", "BBDC3.SA", "CSNA3.SA", "ENEV3.SA", "MBRF3.SA",
    "CPFE3.SA", "EGIE3.SA", "GOAU4.SA", "KLBN11.SA","ISAE4.SA", "FLRY3.SA", "MRVE3.SA", "CVCB3.SA",
    "YDUQ3.SA", "COGN3.SA"
]

import requests

class BreadthAnalyzer:
    def __init__(self, mode='default'):
        self.mode = mode
        self.tickers = IBOV_TICKERS
        self.data = pd.DataFrame()
        self.mas = [9, 21, 50, 80, 200]
        
    def fetch_all_b3_tickers(self):
        url = "https://www.fundamentus.com.br/resultado.php"
        headers = {'User-Agent': 'Mozilla/5.0'}
        print("Scraping Fundamentus for full active market list...")
        
        try:
            r = requests.get(url, headers=headers)
            df_list = pd.read_html(r.text, decimal=',', thousands='.')
            if len(df_list) > 0:
                df = df_list[0]
                if 'Liq.2meses' in df.columns:
                    df = df[df['Liq.2meses'] > 0]
                
                raw_tickers = df['Papel'].tolist()
                formatted_tickers = [f"{t}.SA" for t in raw_tickers]
                print(f"Found {len(formatted_tickers)} active tickers.")
                return formatted_tickers
        except Exception as e:
            print(f"Error scraping tickers: {e}")
            return IBOV_TICKERS # Fallback

    def fetch_data(self):
        if self.mode == 'full':
            self.tickers = self.fetch_all_b3_tickers()
            
        start_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
        print(f"Fetching data for {len(self.tickers)} stocks...")
        

        try:
            data = yf.download(self.tickers, start=start_date, progress=True)['Close']
            
            data = data.dropna(axis=1, how='all')
            
            self.data = data.ffill()
            
            self.tickers = self.data.columns.tolist()
            return True
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False

    def calculate_breadth(self):

        if self.data.empty:
            success = self.fetch_data()
            if not success:
                return {}, pd.DataFrame()

        results = {}
        last_prices = self.data.iloc[-1]
        
        details = pd.DataFrame(index=self.tickers)
        details['Price'] = last_prices
        
        for ma in self.mas:
            ma_df = self.data.rolling(window=ma).mean()
            last_ma = ma_df.iloc[-1]
            
            above_mask = last_prices > last_ma
            
            valid_count = last_prices.notna() & last_ma.notna()
            total_valid = valid_count.sum()
            
            count = above_mask.sum()
            
            pct = count / total_valid if total_valid > 0 else 0
            results[f"MA{ma}"] = pct
            
            details[f'MA{ma}'] = last_ma
            details[f'Above{ma}'] = above_mask
            
        return results, details

if __name__ == "__main__":
    analyzer = BreadthAnalyzer(mode='full')
    metrics, df_details = analyzer.calculate_breadth()
    print("\nMarket Breadth (Full Market):")
    for k, v in metrics.items():
        print(f"{k}: {v:.1%}")
