import pandas as pd
import requests
import io

def test_bcb():
    # Ipeadata Series: GM366_TJOVER366 (Selic daily % a.d.)
    url = "http://www.ipeadata.gov.br/api/odata4/Metadados('GM366_TJOVER366')/Valores"
    try:
        print(f"Fetching {url}...")
        # Ipeadata returns JSON with 'value' key containing list
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data_json = response.json()
        if 'value' in data_json:
            df = pd.DataFrame(data_json['value'])
            print("Data fetched successfully from IPEADATA!")
            print(df.head())
            print(df.tail())
            
            # Columns usually: VALDATA, VALVALOR
            print(df.info())
        else:
            print("JSON structure unexpected")
            print(data_json.keys())
        
    except Exception as e:
        print(f"Error: {e}")
        if 'response' in locals():
            print(f"Status Code: {response.status_code}")

if __name__ == "__main__":
    test_bcb()
