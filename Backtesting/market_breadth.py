
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Major liquid stocks in Ibovespa (Approx top 50-60 by weight/liquidity)
# This serves as a good proxy for the index breadth.
IBOV_TICKERS = [
    "VALE3.SA", "PETR4.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "ELET3.SA", "RENT3.SA",
    "WEGE3.SA", "BPAC11.SA", "ITSA4.SA", "SUZB3.SA", "HAPV3.SA", "JBSS3.SA", "RADL3.SA", "RDOR3.SA",
    "EQTL3.SA", "PRIO3.SA", "RAIL3.SA", "LREN3.SA", "B3SA3.SA", "GGBR4.SA", "VIVT3.SA", "UGPA3.SA",
    "CSAN3.SA", "BBSE3.SA", "ASAI3.SA", "SBSP3.SA", "CMIG4.SA", "VBBR3.SA", "HYPE3.SA", "CPLE6.SA",
    "TOTS3.SA", "EMBR3.SA", "CCRO3.SA", "CIEL3.SA", "MULT3.SA", "TIMS3.SA", "PETR3.SA", "ELET6.SA",
    "BBDC3.SA", "CSNA3.SA", "ENEV3.SA", "BRFS3.SA", "CPFE3.SA", "EGIE3.SA", "GOAU4.SA", "KLBN11.SA",
    "TRPL4.SA", "FLRY3.SA", "MRVE3.SA", "AZUL4.SA", "CVCB3.SA", "GOLL4.SA", "YDUQ3.SA", "COGN3.SA"
]

import requests

class BreadthAnalyzer:
    def __init__(self, mode='default'):
        self.mode = mode
        self.tickers = IBOV_TICKERS
        self.data = pd.DataFrame()
        self.mas = [9, 21, 50, 80, 200]
        
    def fetch_all_b3_tickers(self):
        """Scrapes Fundamentus to get all B3 tickers with liquidity > 0"""
        url = "https://www.fundamentus.com.br/resultado.php"
        headers = {'User-Agent': 'Mozilla/5.0'}
        print("Scraping Fundamentus for full active market list...")
        
        try:
            r = requests.get(url, headers=headers)
            df_list = pd.read_html(r.text, decimal=',', thousands='.')
            if len(df_list) > 0:
                df = df_list[0]
                # Filter for liquidity > 0 to ensure active stocks
                if 'Liq.2meses' in df.columns:
                    df = df[df['Liq.2meses'] > 0]
                
                raw_tickers = df['Papel'].tolist()
                # Append .SA
                formatted_tickers = [f"{t}.SA" for t in raw_tickers]
                print(f"Found {len(formatted_tickers)} active tickers.")
                return formatted_tickers
        except Exception as e:
            print(f"Error scraping tickers: {e}")
            return IBOV_TICKERS # Fallback

    def fetch_data(self):
        """Fetches last ~400 days of data."""
        if self.mode == 'full':
            self.tickers = self.fetch_all_b3_tickers()
            
        start_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d')
        print(f"Fetching data for {len(self.tickers)} stocks...")
        
        # Download in batch
        # YFinance handles large lists well, but for 900+ it might be heavy.
        # We'll try one shot first.
        try:
            data = yf.download(self.tickers, start=start_date, progress=True)['Close']
            
            # Drop columns with all NaNs (failed downloads)
            data = data.dropna(axis=1, how='all')
            
            # Forward fill missing data
            self.data = data.ffill()
            
            # Update tickers list to match what we actually have
            self.tickers = self.data.columns.tolist()
            return True
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False

    def calculate_breadth(self):
        """
        Calculates the % of stocks above each Moving Average.
        Returns a dict: { 'MA9': 0.55, 'MA200': 0.80 ... }
        And a DataFrame with details for the latest date.
        """
        if self.data.empty:
            success = self.fetch_data()
            if not success:
                return {}, pd.DataFrame()

        results = {}
        # Get last valid price for each column
        last_prices = self.data.iloc[-1]
        
        # Store individual status for table
        details = pd.DataFrame(index=self.tickers)
        details['Price'] = last_prices
        
        # Check against MAs
        for ma in self.mas:
            # Calculate Rolling Mean
            ma_df = self.data.rolling(window=ma).mean()
            last_ma = ma_df.iloc[-1]
            
            # Compare (handle NaNs automatically)
            above_mask = last_prices > last_ma
            
            # Only count valid comparisons
            valid_count = last_prices.notna() & last_ma.notna()
            total_valid = valid_count.sum()
            
            count = above_mask.sum()
            
            pct = count / total_valid if total_valid > 0 else 0
            results[f"MA{ma}"] = pct
            
            details[f'MA{ma}'] = last_ma
            details[f'Above{ma}'] = above_mask
            
        return results, details

if __name__ == "__main__":
    # Test Full Mode
    analyzer = BreadthAnalyzer(mode='full')
    metrics, df_details = analyzer.calculate_breadth()
    print("\nMarket Breadth (Full Market):")
    for k, v in metrics.items():
        print(f"{k}: {v:.1%}")
