import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime, timedelta
import matplotlib.ticker as mtick
import requests
import traceback
import scipy.stats as stats

class PortfolioBacktester:
    def __init__(self, tickers, initial_investment, monthly_investment, start_date, end_date=None, benchmark_rate=0.10, rf_allocation=0.0, injected_data=None):
        self.tickers = tickers
        self.initial_investment = initial_investment
        self.monthly_investment = monthly_investment
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
        self.benchmark_rate = benchmark_rate
        self.rf_allocation = rf_allocation
        self.data = pd.DataFrame()
        self.dividends = pd.DataFrame()
        self.currency = pd.DataFrame()
        self.price_data = None
        self.div_data = None
        self.daily_dividends = {}
        self.daily_returns_reinvest = []
        self.daily_returns_no_reinvest = []
        self.injected_data = injected_data
        
    def fetch_data(self):
        print(f"Fetching data for: {self.tickers}")
        
        if self.injected_data is not None and not self.injected_data.empty:
            data = self.injected_data
        else:
            data = yf.download(self.tickers, start=self.start_date, end=self.end_date, actions=True, group_by='column')

        if data is None or data.empty:
            raise ValueError(f"Falha Crítica: Tickers não encontrados ou sem dados no período. Verifique se esqueceu o '.SA'")
            
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        if len(self.tickers) > 1:
            self.price_data = data['Close'].ffill().bfill()
            self.div_data = data['Dividends'].fillna(0)
            self.div_data = self.div_data.reindex(columns=self.price_data.columns, fill_value=0.0)
        else:
            ticker = self.tickers[0]
            self.price_data = pd.DataFrame(data['Close']).rename(columns={'Close': ticker}).ffill().bfill()
            self.div_data = pd.DataFrame(data['Dividends']).rename(columns={'Dividends': ticker}).fillna(0)

        us_stocks = [t for t in self.tickers if not t.endswith('.SA')]
        if us_stocks:
            print("Fetching currency data for US stocks...")
            currency_df = yf.download("USDBRL=X", start=self.start_date, end=self.end_date)['Close']
            
            if isinstance(currency_df, pd.DataFrame):
                currency_df = currency_df.iloc[:, 0]
            if currency_df.index.tz is not None:
                currency_df.index = currency_df.index.tz_localize(None)
                
            self.currency_rate = currency_df.reindex(self.price_data.index).ffill().bfill()

            for ticker in us_stocks:
                if ticker in self.price_data.columns:
                    self.price_data[ticker] = self.price_data[ticker] * self.currency_rate
                    if ticker in self.div_data.columns:
                        self.div_data[ticker] = self.div_data[ticker] * self.currency_rate

        print("Fetching Ibovespa data...")
        try:
            ibov_df = yf.download("^BVSP", start=self.start_date, end=self.end_date)['Close']
            if isinstance(ibov_df, pd.DataFrame):
                ibov_df = ibov_df.iloc[:, 0]
            if ibov_df.index.tz is not None:
                ibov_df.index = ibov_df.index.tz_localize(None)
            self.ibov_series = ibov_df.reindex(self.price_data.index).ffill().bfill()
        except Exception as e:
            print(f"Could not fetch Ibovespa: {e}")
            self.ibov_series = None

        self.price_data = self.price_data.dropna(how='all')
        self.div_data = self.div_data.loc[self.price_data.index].fillna(0)
        self.fetch_risk_free_data()

    def fetch_risk_free_data(self):
        print("Fetching historical Risk-Free Rate (Selic) from Ipeadata...")
        url = "http://www.ipeadata.gov.br/api/odata4/Metadados('GM366_TJOVER366')/Valores"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data_json = response.json()
            
            if 'value' in data_json:
                df = pd.DataFrame(data_json['value'])
                df['Date'] = pd.to_datetime(df['VALDATA'], utc=True).dt.tz_convert(None).dt.normalize()
                df.set_index('Date', inplace=True)
                df = df.sort_index()
                
                start_dt = pd.to_datetime(self.start_date)
                end_dt = pd.to_datetime(self.end_date)
                
                df = df.loc[start_dt:end_dt]
                aligned_selic = df['VALVALOR'].reindex(self.price_data.index).ffill().fillna(0)
                
                self.risk_free_daily_series = (1 + aligned_selic / 100) ** (1/252) - 1
                print("Risk-Free data fetched and aligned.")
        except Exception as e:
            print(f"Failed to fetch Risk Free Data: {e}")
            print("Falling back to fixed benchmark rate.")
            daily_fixed = (1 + self.benchmark_rate) ** (1/252) - 1
            self.risk_free_daily_series = pd.Series(daily_fixed, index=self.price_data.index)
            
    def run(self):
        try:
            self.fetch_data()
            dates = self.price_data.index
            prices = self.price_data.values
            divs = self.div_data.values
            n_assets = len(self.tickers)
            n_days = len(dates)
            
            weights = np.array([1.0 / n_assets] * n_assets)
            
            rf_daily = self.risk_free_daily_series.reindex(dates).fillna(0).values
            ibov_ret = np.zeros(n_days)
            if hasattr(self, 'ibov_series') and self.ibov_series is not None:
                ibov_ret = self.ibov_series.pct_change().reindex(dates).fillna(0).values

            months = dates.month
            monthly_mask = np.zeros(n_days, dtype=bool)
            for i in range(1, n_days):
                if months[i] != months[i-1]:
                    monthly_mask[i] = True

            invested_capital = np.zeros(n_days)
            cdi_balance = np.zeros(n_days)
            ibov_balance = np.zeros(n_days)
            port_val_nr = np.zeros(n_days)
            port_val_r = np.zeros(n_days)
            
            daily_divs_received = np.zeros(n_days)

            shares_nr = np.zeros(n_assets)
            shares_r = np.zeros(n_assets)
            cash_nr = 0.0
            cash_r = 0.0

            alloc_rf = self.rf_allocation / 100.0 if self.rf_allocation > 1 else self.rf_allocation
            alloc_eq = 1.0 - alloc_rf

            for i in range(n_days):
                cash_nr *= (1 + rf_daily[i])
                cash_r *= (1 + rf_daily[i])
                
                if i > 0:
                    cdi_balance[i] = cdi_balance[i-1] * (1 + rf_daily[i])
                    ibov_balance[i] = ibov_balance[i-1] * (1 + ibov_ret[i])
                    invested_capital[i] = invested_capital[i-1]

                if i == 0 or monthly_mask[i]:
                    contrib = self.initial_investment if i == 0 else self.monthly_investment
                    invested_capital[i] += contrib
                    cdi_balance[i] += contrib
                    ibov_balance[i] += contrib

                    contrib_eq = contrib * alloc_eq
                    contrib_rf = contrib * alloc_rf

                    cash_nr += contrib_rf
                    cash_r += contrib_rf

                    if contrib_eq > 0:
                        amt_per_asset = contrib_eq * weights
                        valid_p = prices[i] > 0
                        s_bought = np.zeros(n_assets)
                        s_bought[valid_p] = amt_per_asset[valid_p] / prices[i][valid_p]
                        
                        shares_nr += s_bought
                        shares_r += s_bought

                divs_today_nr = np.sum(shares_nr * divs[i])
                divs_today_r = np.sum(shares_r * divs[i])
                
                daily_divs_received[i] = divs_today_nr
                
                cash_nr += divs_today_nr
                
                if divs_today_r > 0:
                    amt_per_asset = divs_today_r * weights
                    valid_p = prices[i] > 0
                    s_bought = np.zeros(n_assets)
                    s_bought[valid_p] = amt_per_asset[valid_p] / prices[i][valid_p]
                    shares_r += s_bought

                port_val_nr[i] = np.sum(shares_nr * prices[i]) + cash_nr
                port_val_r[i] = np.sum(shares_r * prices[i]) + cash_r

            performance = pd.DataFrame({
                'with_reinvest': port_val_r,
                'no_reinvest': port_val_nr,
                'ibov': ibov_balance,
                'cdi': cdi_balance,
                'invested_capital': invested_capital
            }, index=dates)

            df_divs = pd.DataFrame({'divs': daily_divs_received}, index=dates)
            df_divs['year'] = df_divs.index.year
            df_divs['month'] = df_divs.index.month
            div_matrix = df_divs.groupby(['year', 'month'])['divs'].sum().unstack(fill_value=0)

            port_series = performance['with_reinvest']
            daily_rets = port_series.pct_change().fillna(0)
            
            final_val = port_series.iloc[-1]
            total_cap = invested_capital[-1]
            
            days_passed = (dates[-1] - dates[0]).days
            cagr = ((final_val / total_cap) ** (365.0 / days_passed) - 1) if days_passed > 0 else 0
            
            volatility = daily_rets.std() * np.sqrt(252)
            
            cummax = port_series.cummax()
            drawdown = (port_series / cummax) - 1
            max_drawdown = drawdown.min()
            
            if hasattr(self, 'ibov_series') and self.ibov_series is not None:
                ib_ret = self.ibov_series.pct_change().fillna(0)
                cov = np.cov(daily_rets, ib_ret)
                beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else 0
            else:
                beta = 0.0

            stats_dict = {
                'cagr': cagr * 100,
                'volatility': volatility * 100,
                'max_drawdown': max_drawdown * 100,
                'beta': beta
            }

            self.results = pd.DataFrame({
                'With Reinvestment': port_val_r,
                'Without Reinvestment': port_val_nr,
                'Risk Free': cdi_balance
            }, index=dates)
            self.daily_dividends = df_divs[df_divs['divs'] > 0]['divs'].to_dict()
            self.daily_returns_reinvest = daily_rets.values
            self.daily_returns_no_reinvest = performance['no_reinvest'].pct_change().fillna(0).values

            return {
                'performance': performance,
                'div_matrix': div_matrix,
                'stats': stats_dict
            }
            
        except Exception as e:
            traceback.print_exc()
            return None
        
    def display_monthly_income(self):
        if not self.daily_dividends:
            print("No dividends received.")
            return
        df_divs = pd.DataFrame.from_dict(self.daily_dividends, orient='index', columns=['Dividend'])
        df_divs.index = pd.to_datetime(df_divs.index)
        df_divs['Year'] = df_divs.index.year
        df_divs['Month'] = df_divs.index.month
        monthly_pivot = df_divs.pivot_table(index='Year', columns='Month', values='Dividend', aggfunc='sum').fillna(0)
        monthly_pivot['Total'] = monthly_pivot.sum(axis=1)
        month_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
                     7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
        monthly_pivot = monthly_pivot.rename(columns=month_map)
        
        print("\n=== Monthly Dividend Income (BRL) ===")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(monthly_pivot.map(lambda x: f"{x:,.2f}"))
        
    def display_metrics(self):
        m_reinvest = self.calculate_metrics(self.daily_returns_reinvest, self.risk_free_daily_series.values)
        m_no_reinvest = self.calculate_metrics(self.daily_returns_no_reinvest, self.risk_free_daily_series.values)
        print("\n=== Performance Metrics ===")
        print(f"{'Metric':<20} | {'With Reinvest':<15} | {'No Reinvest':<15}")
        print("-" * 56)
        for k in m_reinvest.keys():
            val_r = m_reinvest[k]
            val_nr = m_no_reinvest[k]
            if k in ["Total Return", "CAGR", "Volatility", "Max Drawdown"]:
                fmt_r, fmt_nr = f"{val_r*100:.2f}%", f"{val_nr*100:.2f}%"
            else:
                fmt_r, fmt_nr = f"{val_r:.2f}", f"{val_nr:.2f}"
            print(f"{k:<20} | {fmt_r:<15} | {fmt_nr:<15}")
            
    def plot(self):
        plt.figure(figsize=(12, 6))
        plt.plot(self.results.index, self.results['With Reinvestment'], label='Com Reinvestimento (Cotas)')
        plt.plot(self.results.index, self.results['Without Reinvestment'], label='Sem Reinvestimento (Div. no Caixa)')
        plt.plot(self.results.index, self.results['Risk Free'], label='Somente CDI', linestyle='--')
        plt.title('Backtest de Portfolio (BRL)')
        plt.xlabel('Data')
        plt.ylabel('Valor do Portfolio (R$)')
        
        def currency(x, pos):
            return f'R$ {x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            
        plt.gca().yaxis.set_major_formatter(mtick.FuncFormatter(currency))
        plt.legend()
        plt.grid(True)
        plt.show()

    def calculate_metrics(self, returns_series, risk_free_series=None):
        if len(returns_series) == 0: return {}
        returns = pd.Series(returns_series)
        
        if risk_free_series is not None:
            rf = pd.Series(risk_free_series)
            if len(rf) != len(returns):
                excess_returns = returns - rf.mean()
            else:
                excess_returns = returns - rf
        else:
             rf_fixed = (1 + self.benchmark_rate) ** (1/252) - 1
             excess_returns = returns - rf_fixed

        total_return = (1 + returns).prod() - 1
        n_days = len(returns)
        cagr = (1 + total_return) ** (252 / n_days) - 1 if n_days > 0 else 0.0
        volatility = returns.std() * (252 ** 0.5)
        
        wealth_index = (1 + returns).cumprod()
        drawdown = (wealth_index - wealth_index.cummax()) / wealth_index.cummax()
        
        return {
            "Total Return": total_return,
            "CAGR": cagr,
            "Volatility": volatility,
            "Max Drawdown": drawdown.min()
        }

def render():
    st.header("Portfolio Backtester")

    col1, col2 = st.columns(2)
    with col1:
        tickers_input = st.text_input("Tickers separados por espaço (ex: ABCB4 BBAS3 BBSE3):", value="ABCB4 BBAS3 BBSE3 CMIG4 ITUB3 KLBN11 TIMS3 TAEE11", key="bt_tickers")
        initial_inv = st.number_input("Investimento Inicial (R$):", min_value=0.0, value=10000.0, step=1000.0, key="bt_initial_inv")
        monthly_inv = st.number_input("Investimento Mensal (R$):", min_value=0.0, value=1000.0, step=100.0, key="bt_monthly_inv")
    
    with col2:
        start_d = st.date_input("Data de Início:", value=datetime(2018, 1, 1), key="bt_start_date")
        end_d = st.date_input("Data de Fim:", value=datetime.now(), key="bt_end_date")
        rf_alloc = st.slider("Alocação em Renda Fixa (%):", min_value=0.0, max_value=100.0, value=0.0, step=5.0, key="bt_rf_alloc") / 100.0

    if st.button("Rodar Backtest do Portfólio"):
        tickers_list = [t if t.endswith(".SA") else f"{t}.SA" for t in tickers_input.replace(',', ' ').strip().upper().split()]
        if not tickers_list:
            st.error("Por favor, insira pelo menos um ticker.")
            return
        
        with st.spinner("Buscando dados históricos e calculando retornos..."):
            try:
                backtester = PortfolioBacktester(
                    tickers=tickers_list,
                    initial_investment=initial_inv,
                    monthly_investment=monthly_inv,
                    start_date=start_d.strftime('%Y-%m-%d'),
                    end_date=end_d.strftime('%Y-%m-%d'),
                    rf_allocation=rf_alloc
                )
                
                backtester.fetch_data()
                results_dict = backtester.run()
                
                if results_dict is None or 'performance' not in results_dict or results_dict['performance'].empty:
                    st.error("Nenhum dado gerado para o período selecionado.")
                    return
                
                performance = results_dict['performance']
                stats = results_dict['stats']
                
                st.subheader("Métricas de Desempenho")
                final_row = performance.iloc[-1]
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Patrimônio Final (Com Reinvestimento)", f"R$ {final_row['with_reinvest']:.2f}")
                m2.metric("Patrimônio Final (Sem Reinvestimento)", f"R$ {final_row['no_reinvest']:.2f}")
                m3.metric("Total Injetado (Capital)", f"R$ {final_row['invested_capital']:.2f}")
                
                m4, m5, m6, m7 = st.columns(4)
                m4.metric("CAGR (Retorno Anualizado)", f"{stats['cagr']:.2f}%")
                m5.metric("Volatilidade Anual", f"{stats['volatility']:.2f}%")
                m6.metric("Max Drawdown", f"{stats['max_drawdown']:.2f}%")
                m7.metric("Beta (vs Ibovespa)", f"{stats['beta']:.2f}")
                
                st.subheader("Evolução Patrimonial ao Longo do Tempo")
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(performance.index, performance['with_reinvest'], label="Com Reinvestimento de Dividendos", linewidth=2)
                ax.plot(performance.index, performance['no_reinvest'], label="Sem Reinvestimento de Dividendos", linewidth=1.5, linestyle="--")
                ax.plot(performance.index, performance['invested_capital'], label="Capital Injetado", linewidth=1.5, color="gray")
                
                ax.set_title("Evolução do Portfólio")
                ax.set_xlabel("Data")
                ax.set_ylabel("Valor (R$)")
                ax.legend()
                ax.grid(True, linestyle="--", alpha=0.5)
                
                col_chart, _ = st.columns([3, 1])
                with col_chart:
                    st.pyplot(fig, use_container_width=True)
                
                # --- MATRIZ DE DIVIDENDOS MENSAIS ---
                if backtester.daily_dividends:
                    st.subheader("Recebimento Mensal de Dividendos (R$)")
                    
                    df_divs = pd.DataFrame.from_dict(backtester.daily_dividends, orient='index', columns=['Dividend'])
                    df_divs.index = pd.to_datetime(df_divs.index)
                    df_divs['Year'] = df_divs.index.year
                    df_divs['Month'] = df_divs.index.month
                    monthly_pivot = df_divs.pivot_table(index='Year', columns='Month', values='Dividend', aggfunc='sum').fillna(0)
                    
                    # Garantir que todos os meses de 1 a 12 estejam representados
                    for m in range(1, 13):
                        if m not in monthly_pivot.columns:
                            monthly_pivot[m] = 0.0
                    
                    # Reordenar colunas
                    monthly_pivot = monthly_pivot[list(range(1, 13))]
                    
                    # Mapear nomes dos meses
                    month_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
                                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
                    monthly_pivot = monthly_pivot.rename(columns=month_map)
                    
                    # Adicionar total
                    monthly_pivot['Total'] = monthly_pivot.sum(axis=1)
                    
                    # Exibir tabela formatada
                    st.dataframe(
                        monthly_pivot,
                        use_container_width=True,
                        column_config={
                            col: st.column_config.NumberColumn(col, format="R$ %.2f") 
                            for col in monthly_pivot.columns
                        }
                    )
                
            except Exception as e:
                st.error(f"Erro ao executar o backtest: {str(e)}")