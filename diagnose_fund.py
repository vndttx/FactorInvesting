"""
Diagnose why 13.823.084/0001-05 is not loading
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'Backtesting'))

import fund_tool
import pandas as pd

cnpj = "13.823.084/0001-05"
clean_cnpj = ''.join(filter(str.isdigit, cnpj))

print(f"Diagnosing CNPJ: {cnpj} ({clean_cnpj})")

ff = fund_tool.HybridFundFetcher()

# 1. Check Metadata
print("\n--- 1. Metadata Check ---")
meta = ff.get_fund_metadata(cnpj)
if meta:
    print("✓ Found in CVM Cadastral Data")
    print(f"  Name: {meta['name']}")
    print(f"  Status: {meta['status']}")
    print(f"  Start Date: {meta['start_date']}")
    if 'end_date' in meta:
        print(f"  End Date: {meta.get('end_date')}")
        
    start_year = meta['start_date'].year
    print(f"  Inception Year: {start_year}")
else:
    print("✗ Not found in CVM Cadastral Data")
    # Search for partial match?
    
# 2. Check History
print("\n--- 2. History Check ---")
# Try to fetch just one month where it SHOULD exist (e.g. 2023 or 2024)
year = 2023
print(f"Trying to fetch data for {year}...")

hist = ff.get_fund_history(cnpj, start_year=year)

if not hist.empty:
    print(f"✓ Found {len(hist)} records")
    print(hist.head())
    print(hist.tail())
else:
    print("✗ No history found")
    
    # Debug: Check if it's cached as empty
    cache_file = ff.cache_dir / f"{clean_cnpj}.parquet"
    if cache_file.exists():
        print(f"  Cache file exists: {cache_file}")
    else:
        print("  No cache file found")
