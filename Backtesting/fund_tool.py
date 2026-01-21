import pandas as pd
import requests
import io
import zipfile
import yfinance as yf
from datetime import datetime
import warnings
import os
from pathlib import Path

# Suppress warnings
warnings.filterwarnings("ignore")

class HybridFundFetcher:
    """
    Hybrid fund fetcher using multiple strategies:
    1. brfunds (comparadordefundos.com.br) - FAST
    2. Local cache - FASTER on repeat
    3. CVM Open Data - COMPREHENSIVE fallback
    """
    def __init__(self):
        self.base_url_fi = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"
        self.base_url_cad = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
        
        # Setup cache directory
        self.cache_dir = Path("cache/funds")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_fund_metadata(self, cnpj):
        """Try brfunds first, then CVM"""
        clean_cnpj = ''.join(filter(str.isdigit, cnpj))
        
        # Try brfunds first
        try:
            from brfunds import FundData
            print("Fetching metadata from brfunds (fast)...")
            fd = FundData(cnpj=clean_cnpj)
            info = fd.info()
            
            if info and not info.empty:
                meta = {
                    'name': info.get('fund_name', 'N/A'),
                    'start_date': pd.to_datetime(info.get('dt_comptc_inicial', None)),
                    'status': 'EM FUNCIONAMENTO NORMAL',  # brfunds only has active funds
                    'class': info.get('classe', 'N/A')
                }
                return meta
        except Exception as e:
            print(f"brfunds metadata failed: {e}")
        
        # Fallback to CVM
        print("Falling back to CVM for metadata...")
        return self._get_metadata_from_cvm(cnpj)
    
    def _get_metadata_from_cvm(self, cnpj):
        """Original CVM metadata fetcher"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            df_cad = pd.read_csv(self.base_url_cad, sep=';', encoding='ISO-8859-1', 
                                 usecols=['CNPJ_FUNDO', 'DENOM_SOCIAL', 'DT_CONST', 'SIT', 'CLASSE'])
            
            df_cad['CNPJ_FUNDO'] = df_cad['CNPJ_FUNDO'].str.replace(r'[^0-9]', '', regex=True)
            clean_cnpj = ''.join(filter(str.isdigit, cnpj))
            
            fund = df_cad[df_cad['CNPJ_FUNDO'] == clean_cnpj]
            
            if fund.empty:
                return None
            
            fund = fund.iloc[0]
            
            meta = {
                'name': fund['DENOM_SOCIAL'],
                'start_date': pd.to_datetime(fund['DT_CONST']),
                'status': fund['SIT'],
                'class': fund['CLASSE']
            }
            return meta
            
        except Exception as e:
            print(f"Error fetching CVM metadata: {e}")
            return None
    
    def get_fund_history(self, cnpj, start_year=None):
        """
        Hybrid fetcher: brfunds → cache → CVM
        """
        clean_cnpj = ''.join(filter(str.isdigit, cnpj))
        
        # Try brfunds first (FASTEST)
        try:
            from brfunds import FundData
            print("Fetching history from brfunds (fast)...")
            fd = FundData(cnpj=clean_cnpj)
            earnings = fd.earnings()
            
            if earnings is not None and not earnings.empty:
                # brfunds returns: Date, Quota Value, Net Asset, etc.
                # Standardize to our format
                df = earnings.copy()
                
                # Find quota column
                quota_col = None
                for col in df.columns:
                    if 'quota' in col.lower() or 'cota' in col.lower():
                        quota_col = col
                        break
                
                if quota_col:
                    df = df.rename(columns={quota_col: 'VL_QUOTA'})
                    df.index = pd.to_datetime(df.index)
                    df.index.name = 'DT_COMPTC'
                    
                    # Filter by start_year if specified
                    if start_year:
                        df = df[df.index.year >= start_year]
                    
                    return df[['VL_QUOTA']]
        except Exception as e:
            print(f"brfunds history failed: {e}")
        
        # Check cache
        cached = self._load_from_cache(clean_cnpj)
        if cached is not None and not cached.empty:
            print("Loading from cache...")
            if start_year:
                cached = cached[cached.index.year >= start_year]
            return cached
        
        # Fallback to CVM (slower but comprehensive)
        print("Downloading from CVM (slower)...")
        df = self._get_history_from_cvm(cnpj, start_year)
        
        # Cache the result
        if not df.empty:
            self._save_to_cache(clean_cnpj, df)
        
        return df
    
    def _load_from_cache(self, clean_cnpj):
        """Load fund history from local cache"""
        # Try parquet first, then pickle as fallback
        for ext, loader in [('.parquet', 'parquet'), ('.pkl', 'pickle')]:
            cache_file = self.cache_dir / f"{clean_cnpj}{ext}"
            if cache_file.exists():
                try:
                    # Check if cache is fresh (< 1 day old)
                    age_hours = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 3600
                    if age_hours < 24:
                        if loader == 'parquet':
                            return pd.read_parquet(cache_file)
                        else:
                            return pd.read_pickle(cache_file)
                except Exception as e:
                    print(f"Cache load failed ({ext}): {e}")
        return None
    
    def _save_to_cache(self, clean_cnpj, df):
        """Save fund history to local cache"""
        try:
            # Try parquet first (fastest)
            cache_file = self.cache_dir / f"{clean_cnpj}.parquet"
            df.to_parquet(cache_file)
        except Exception:
            try:
                # Fallback to pickle if parquet fails
                cache_file = self.cache_dir / f"{clean_cnpj}.pkl"
                df.to_pickle(cache_file)
            except Exception as e:
                print(f"Cache save failed: {e}")
    
    def _get_history_from_cvm(self, cnpj, start_year=None):
        """Original CVM history fetcher (unchanged from before)"""
        clean_cnpj = ''.join(filter(str.isdigit, cnpj))
        
        if start_year is None:
            start_year = datetime.now().year - 2
            
        current_year = datetime.now().year
        current_month = datetime.now().month
        all_data = []
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        for year in range(int(start_year), current_year + 1):
            start_month = 1
            end_month = 12 if year < current_year else current_month
            
            for month in range(start_month, end_month + 1):
                url = f"{self.base_url_fi}/inf_diario_fi_{year}{month:02d}.zip"
                try:
                    print(f"Downloading {year}-{month:02d}...")
                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        csv_name = [f for f in z.namelist() if f.endswith('.csv')][0]
                        with z.open(csv_name) as f:
                            df_month = pd.read_csv(f, sep=';', encoding='ISO-8859-1', nrows=0)
                            available_cols = df_month.columns.tolist()
                            
                            cnpj_col = date_col = quota_col = patrimony_col = None
                            
                            for col in available_cols:
                                col_upper = col.upper()
                                # Match both CNPJ_FUNDO and CNPJ_FUNDO_CLASSE
                                if 'CNPJ' in col_upper and 'FUNDO' in col_upper and cnpj_col is None:
                                    cnpj_col = col
                                elif 'DT_COMPTC' in col_upper or ('DATA' in col_upper and 'COMPET' in col_upper):
                                    date_col = col
                                elif 'VL_QUOTA' in col_upper or 'VALOR' in col_upper and 'COTA' in col_upper:
                                    quota_col = col
                                elif 'VL_PATRIM' in col_upper or ('PATRIMON' in col_upper and 'LIQUID' in col_upper):
                                    patrimony_col = col
                            
                            if not all([cnpj_col, date_col, quota_col]):
                                continue
                            
                            f.seek(0)
                            cols_to_use = [cnpj_col, date_col, quota_col]
                            if patrimony_col:
                                cols_to_use.append(patrimony_col)
                                
                            df_month = pd.read_csv(f, sep=';', encoding='ISO-8859-1', usecols=cols_to_use)
                    
                    df_month = df_month.rename(columns={
                        cnpj_col: 'CNPJ_FUNDO',
                        date_col: 'DT_COMPTC',
                        quota_col: 'VL_QUOTA'
                    })
                    if patrimony_col:
                        df_month = df_month.rename(columns={patrimony_col: 'VL_PATRIM_LIQ'})
                    
                    df_month['CNPJ_FUNDO'] = df_month['CNPJ_FUNDO'].astype(str).str.replace(r'[^0-9]', '', regex=True)
                    fund_data = df_month[df_month['CNPJ_FUNDO'] == clean_cnpj].copy()
                    
                    if not fund_data.empty:
                        all_data.append(fund_data)
                        
                except requests.exceptions.HTTPError:
                    pass
                except Exception as e:
                    print(f"Error {year}-{month:02d}: {e}")
                
        if not all_data:
            return pd.DataFrame()
            
        final_df = pd.concat(all_data, ignore_index=True)
        final_df['DT_COMPTC'] = pd.to_datetime(final_df['DT_COMPTC'], errors='coerce')
        final_df = final_df.dropna(subset=['DT_COMPTC'])
        final_df = final_df.sort_values('DT_COMPTC')
        final_df = final_df.set_index('DT_COMPTC')
        
        return_cols = ['VL_QUOTA']
        if 'VL_PATRIM_LIQ' in final_df.columns:
            return_cols.append('VL_PATRIM_LIQ')
        
        return final_df[return_cols]

class BenchmarkFetcher:
    def get_cdi(self, start_date):
        """Fetches CDI from BCB"""
        try:
            # Format start date for API (DD/MM/YYYY)
            if isinstance(start_date, str):
                sdate = pd.to_datetime(start_date).strftime('%d/%m/%Y')
            else:
                sdate = start_date.strftime('%d/%m/%Y')
            
            # API requires end date too, use today
            edate = datetime.now().strftime('%d/%m/%Y')
            
            # BCB often blocks scripts, so we add a User-Agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Workaround for SSL errors often seen with BCB
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial={sdate}&dataFinal={edate}"
            
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            
            if response.status_code != 200:
                print(f"CDI API failed: {response.status_code} - {response.text[:100]}")
                return pd.Series(dtype=float)

            try:
                data = response.json()
            except Exception as e:
                print(f"CDI JSON parse error: {e}. Content start: {response.text[:100]}")
                return pd.Series(dtype=float)
            
            if not data:
                return pd.Series(dtype=float)
            
            # If data is a list of dicts (standard)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                # If single dict or scalar, wrap in list
                df = pd.DataFrame([data])
            
            # Verify columns exist
            if 'data' not in df.columns or 'valor' not in df.columns:
                print(f"CDI API structure unexpected. Cols: {df.columns}. Data sample: {data[:1] if isinstance(data, list) else data}")
                return pd.Series(dtype=float)

            df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
            
            df = df[df['data'] >= pd.to_datetime(start_date)]
            
            if df.empty:
                return pd.Series(dtype=float)
            
            df = df.set_index('data')
            df['factor'] = 1 + (df['valor'] / 100)
            df['CDI Index'] = df['factor'].cumprod()
            
            return df['CDI Index']
            
        except Exception as e:
            print(f"Error fetching CDI: {e}")
            return pd.Series(dtype=float)

    def get_ipca(self, start_date):
        """Fetches IPCA from BCB"""
        try:
            # IPCA is Series 433
            # Format start date for API (DD/MM/YYYY)
            if isinstance(start_date, str):
                sdate = pd.to_datetime(start_date).strftime('%d/%m/%Y')
            else:
                sdate = start_date.strftime('%d/%m/%Y')
            
            edate = datetime.now().strftime('%d/%m/%Y')
            
            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={sdate}&dataFinal={edate}"
            
            # Add same headers/ssl fix for IPCA
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            data = response.json()
            
            if not data:
                return pd.Series(dtype=float)
                
            df = pd.DataFrame(data)
            df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
            
            df = df.set_index('data')
            df = df.sort_index()
            
            # IPCA is monthly %
            df['factor'] = 1 + (df['valor'] / 100)
            
            # Convert start_date to datetime if str, for filtering
            if isinstance(start_date, str):
                 start_dt = pd.to_datetime(start_date)
            else:
                 start_dt = start_date
            
            df = df[df.index >= start_dt]
            
            df['cum_factor'] = df['factor'].cumprod()
            df['IPCA'] = df['cum_factor'] * 100
            
            return df['IPCA']
            
        except Exception as e:
            print(f"Error fetching IPCA: {e}")
            return pd.Series(dtype=float)

    def get_ibov(self, start_date):
        try:
            import time
            time.sleep(1)
            
            ibov = yf.download("^BVSP", start=start_date, progress=False, auto_adjust=True)
            
            if ibov.empty:
                return pd.Series(dtype=float)
            
            if isinstance(ibov.columns, pd.MultiIndex):
                ibov = ibov.xs('Close', axis=1, level=0)
            else:
                ibov = ibov['Close']
            return ibov
        except Exception as e:
            print(f"Error fetching IBOV: {e}")
            return pd.Series(dtype=float)

# Backwards compatibility: keep original class names
FundFetcher = HybridFundFetcher
