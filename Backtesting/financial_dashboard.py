import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import yfinance as yf
import threading
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.ticker as mtick


current_dir = os.path.dirname(os.path.abspath(__file__))
backtesting_dir = os.path.join(current_dir, 'Backtesting')
if backtesting_dir not in sys.path:
    sys.path.append(backtesting_dir)


try:
    import valuation
    import backtest_tool
    import optimization_tool
    import market_breadth
    import rrg_tool
    import pandas as pd
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
except ImportError as e:
    messagebox.showerror("Import Error", f"Could not import modules from Backtesting folder.\nError: {e}")
    sys.exit(1)


class FinancialDashboardArgs(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Factor Investing Dashboard")
        self.geometry("900x720")


        style = ttk.Style()
        style.theme_use('clam')


        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)


        self.create_valuation_tab()
        self.create_backtest_tab()
        self.create_optimization_tab()
        self.create_breadth_tab()
        self.create_rrg_tab()


    def create_valuation_tab(self):
        self.tab_val = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_val, text="Stock Valuation")


        input_frame = ttk.LabelFrame(self.tab_val, text="Input", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)


        ttk.Label(input_frame, text="Ticker (e.g., PETR4):").pack(side='left', padx=5)
        self.val_ticker_entry = ttk.Entry(input_frame, width=15)
        self.val_ticker_entry.pack(side='left', padx=5)
        self.val_ticker_entry.bind('<Return>', lambda e: self.run_valuation())


        self.btn_analyze = ttk.Button(input_frame, text="Analyze", command=self.run_valuation)
        self.btn_analyze.pack(side='left', padx=5)


        results_frame = ttk.LabelFrame(self.tab_val, text="Valuation Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=10, pady=10)


        columns = ("Method", "Implied Value", "Upside", "Status", "Notes")
        self.val_tree = ttk.Treeview(results_frame, columns=columns, show='headings')


        for col in columns:
            self.val_tree.heading(col, text=col)
            self.val_tree.column(col, width=120)


        self.val_tree.column("Method", width=150)
        self.val_tree.column("Notes", width=250)


        self.val_tree.pack(fill='both', expand=True)


        self.val_status_label = ttk.Label(results_frame, text="Ready.", font=('Arial', 9, 'italic'))
        self.val_status_label.pack(pady=5, anchor='w')


    def create_backtest_tab(self):
        self.tab_bt = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bt, text="Portfolio Backtest")


        input_frame = ttk.LabelFrame(self.tab_bt, text="Configuration", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)


        ttk.Label(input_frame, text="Tickers (comma sep):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.bt_tickers_entry = ttk.Entry(input_frame, width=50)
        self.bt_tickers_entry.grid(row=0, column=1, columnspan=3, sticky='w', padx=5, pady=5)
        self.bt_tickers_entry.insert(0, "BBAS3, BBSE3, CMIG4, CXSE3, PETR4")


        ttk.Label(input_frame, text="Initial Invest (BRL):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.bt_initial_entry = ttk.Entry(input_frame, width=15)
        self.bt_initial_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.bt_initial_entry.insert(0, "1000")


        ttk.Label(input_frame, text="Monthly Invest (BRL):").grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.bt_monthly_entry = ttk.Entry(input_frame, width=15)
        self.bt_monthly_entry.grid(row=1, column=3, sticky='w', padx=5, pady=5)
        self.bt_monthly_entry.insert(0, "600")


        ttk.Label(input_frame, text="Start Date (YYYY-MM-DD):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.bt_start_entry = ttk.Entry(input_frame, width=15)
        self.bt_start_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        self.bt_start_entry.insert(0, "2015-01-01")


        ttk.Label(input_frame, text="Risk Free Alloc (%):").grid(row=2, column=2, sticky='w', padx=5, pady=5)
        self.bt_rf_alloc_entry = ttk.Entry(input_frame, width=15)
        self.bt_rf_alloc_entry.grid(row=2, column=3, sticky='w', padx=5, pady=5)
        self.bt_rf_alloc_entry.insert(0, "0")


        self.btn_run_bt = ttk.Button(input_frame, text="Run Backtest", command=self.run_backtest_thread)
        self.btn_run_bt.grid(row=3, column=3, sticky='e', padx=5, pady=5)


        self.bt_results_frame = ttk.LabelFrame(self.tab_bt, text="Performance Outcomes", padding=10)
        self.bt_results_frame.pack(fill='both', expand=True, padx=10, pady=10)


        self.bt_notebook = ttk.Notebook(self.bt_results_frame)
        self.bt_notebook.pack(fill='both', expand=True)


        self.bt_tab_summary = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(self.bt_tab_summary, text="Summary & Chart")


        self.bt_text_output = tk.Text(self.bt_tab_summary, height=10, width=80)
        self.bt_text_output.pack(side='left', fill='y', padx=5, pady=5)


        self.bt_chart_frame = ttk.Frame(self.bt_tab_summary)
        self.bt_chart_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)


        self.bt_tab_divs = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(self.bt_tab_divs, text="Monthly Dividends")


        self.div_tree = ttk.Treeview(self.bt_tab_divs, show='headings')
        self.div_tree.pack(fill='both', expand=True, padx=5, pady=5)


        vsb = ttk.Scrollbar(self.bt_tab_divs, orient="vertical", command=self.div_tree.yview)
        vsb.pack(side='right', fill='y')
        hsb = ttk.Scrollbar(self.bt_tab_divs, orient="horizontal", command=self.div_tree.xview)
        hsb.pack(side='bottom', fill='x')
        self.div_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)


    def run_valuation(self):
        ticker_input = self.val_ticker_entry.get().strip().upper()
        if not ticker_input:
            messagebox.showwarning("Input Error", "Please enter a ticker symbol.")
            return


        if not ticker_input.endswith(".SA"):
            ticker = f"{ticker_input}.SA"
        else:
            ticker = ticker_input


        self.val_status_label.config(text=f"Fetching data for {ticker}...")
        self.val_tree.delete(*self.val_tree.get_children())
        self.update_idletasks()


        t = threading.Thread(target=self._process_valuation, args=(ticker,))
        t.start()


    def _process_valuation(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            data = valuation.get_financial_data(stock)


            if not data:
                self.after(0, lambda: messagebox.showerror("Error", "Could not fetch data (check ticker or internet)."))
                self.after(0, lambda: self.val_status_label.config(text="Error."))
                return


            rows = []


            price = data['current_price']


            bazin_price, bazin_dy = valuation.calculate_bazin(data)
            if bazin_price:
                upside = ((bazin_price - price) / price) * 100
                status = "Cheap" if bazin_price > price else "Expensive"
                rows.append(("Décio Bazin", f"R$ {bazin_price:.2f}", f"{upside:+.2f}%", status, f"Avg Yield: {bazin_dy:.2f}% (Target 6%)"))
            else:
                rows.append(("Décio Bazin", "N/A", "-", "-", "Insufficient Data"))


            graham_price = valuation.calculate_graham(data)
            if graham_price:
                upside = ((graham_price - price) / price) * 100
                status = "Cheap" if graham_price > price else "Expensive"
                rows.append(("Graham Number", f"R$ {graham_price:.2f}", f"{upside:+.2f}%", status, "Sqrt(22.5 * EPS * BVPS)"))
            else:
                rows.append(("Graham Number", "N/A", "-", "-", "Neg Earnings/Book"))


            pe = data.get('pe_ratio')
            eps = data.get('eps')
            if pe and eps:
                fair_pe = 15 * eps
                upside_pe = ((fair_pe - price) / price) * 100
                status_pe = "Cheap" if fair_pe > price else "Expensive"
                rows.append(("P/E Ratio (15x)", f"R$ {fair_pe:.2f}", f"{upside_pe:+.2f}%", status_pe, f"Current P/E: {pe:.2f}"))
            else:
                rows.append(("P/E Ratio", "N/A", "-", "-", "-"))


            peg, peg_note = valuation.calculate_peg(data)
            if peg:
                status = "Undervalued" if peg < 1 else "Overvalued"
                rows.append(("PEG Ratio", f"{peg:.2f}", "-", status, f"<1.0 is Good ({peg_note})"))
            else:
                rows.append(("PEG Ratio", "N/A", "-", "-", "-"))


            self.after(0, lambda: self._update_val_table(rows, price))


        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))


    def _update_val_table(self, rows, current_price):
        for row in rows:
            self.val_tree.insert("", "end", values=row)
        self.val_status_label.config(text=f"Analysis complete. Current Price: R$ {current_price:.2f}")


    def run_backtest_thread(self):


        tickers_str = self.bt_tickers_entry.get()
        init_str = self.bt_initial_entry.get()
        monthly_str = self.bt_monthly_entry.get()
        start_date = self.bt_start_entry.get()
        rf_alloc_str = self.bt_rf_alloc_entry.get()


        if not tickers_str or not init_str or not monthly_str or not start_date or not rf_alloc_str:
            messagebox.showwarning("Missing Inputs", "Please fill all fields.")
            return


        raw_tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        tickers = []
        for t in raw_tickers:


            if '.' in t or '=' in t:
                tickers.append(t)
            else:


                tickers.append(f"{t}.SA")


        try:
            initial = float(init_str)
            monthly = float(monthly_str)
            rf_alloc = float(rf_alloc_str)
            if rf_alloc < 0 or rf_alloc > 100:
                 messagebox.showerror("Invalid Input", "Risk Free Allocation must be between 0 and 100.")
                 return
            rf_alloc_decimal = rf_alloc / 100.0


        except ValueError:
            messagebox.showerror("Invalid Number", "Investments/Allocation must be numbers.")
            return


        self.btn_run_bt.config(state='disabled')
        self.bt_text_output.delete("1.0", tk.END)
        self.bt_text_output.insert(tk.END, "Running backtest... Please wait.\n")


        t = threading.Thread(target=self._process_backtest, args=(tickers, initial, monthly, start_date, rf_alloc_decimal))
        t.start()


    def _process_backtest(self, tickers, initial, monthly, start_date, rf_alloc_decimal):
        try:
            bt = backtest_tool.PortfolioBacktester(tickers, initial, monthly, start_date, risk_free_allocation=rf_alloc_decimal)
            bt.run()


            m_reinvest = bt.calculate_metrics(bt.daily_returns_reinvest, bt.risk_free_daily_series.values)
            m_no_reinvest = bt.calculate_metrics(bt.daily_returns_no_reinvest, bt.risk_free_daily_series.values)


            beta_reinvest = bt.calculate_beta(bt.daily_returns_reinvest)
            beta_no_reinvest = bt.calculate_beta(bt.daily_returns_no_reinvest)


            m_reinvest["Beta (vs Ibov)"] = beta_reinvest
            m_no_reinvest["Beta (vs Ibov)"] = beta_no_reinvest


            output = []
            output.append("\n=== PERFORMANCE METRICS ===\n")
            output.append(f"{'Metric':<25} | {'With Reinvest':<15} | {'No Reinvest':<15}")
            output.append("-" * 65)


            for k in m_reinvest.keys():
                val_r = m_reinvest[k]
                val_nr = m_no_reinvest[k]


                if k in ["Total Return", "CAGR", "Volatility", "Max Drawdown"]:
                    fmt_r = f"{val_r*100:.2f}%"
                    fmt_nr = f"{val_nr*100:.2f}%"
                else:
                    fmt_r = f"{val_r:.2f}"
                    fmt_nr = f"{val_nr:.2f}"
                output.append(f"{k:<25} | {fmt_r:<15} | {fmt_nr:<15}")


            output.append("\n\n=== FINAL PORTFOLIO VALUES (BRL) ===")
            final = bt.results.iloc[-1]
            for k, v in final.items():
                output.append(f"{k:<25}: R$ {v:,.2f}")


            report = "\n".join(output)


            self.after(0, lambda: self._show_bt_results(report, bt))


        except Exception as e:
            self.after(0, lambda: self._bt_error(str(e)))


    def _show_bt_results(self, report, bt_obj):
        self.bt_text_output.delete("1.0", tk.END)
        self.bt_text_output.insert(tk.END, report)
        self.btn_run_bt.config(state='normal')


        for widget in self.bt_chart_frame.winfo_children():
            widget.destroy()


        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)


        results = bt_obj.results
        ax.plot(results.index, results['With Reinvestment'], label='With Divs')
        ax.plot(results.index, results['Without Reinvestment'], label='No Reinvest')
        if 'Ibovespa' in results.columns:
             ax.plot(results.index, results['Ibovespa'], label='Ibovespa', linestyle='-', color='gray', alpha=0.6)
        ax.plot(results.index, results['Risk Free'], label='Risk Free', linestyle='--')


        ax.set_title('Portfolio Performance')
        ax.set_xlabel('Date')
        ax.set_ylabel('Value (BRL)')
        ax.legend()
        ax.grid(True)


        def currency(x, pos):
            return f'R$ {x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(currency))


        fig.tight_layout()


        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.bt_chart_frame)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill='both', expand=True)


        self._populate_div_table(bt_obj)


    def _populate_div_table(self, bt_obj):


        self.div_tree.delete(*self.div_tree.get_children())
        self.div_tree["columns"] = []


        if not bt_obj.daily_dividends:


             return


        df_divs = pd.DataFrame.from_dict(bt_obj.daily_dividends, orient='index', columns=['Dividend'])
        df_divs.index = pd.to_datetime(df_divs.index)
        df_divs['Year'] = df_divs.index.year
        df_divs['Month'] = df_divs.index.month


        monthly_pivot = df_divs.pivot_table(index='Year', columns='Month', values='Dividend', aggfunc='sum').fillna(0)


        monthly_pivot['Total'] = monthly_pivot.sum(axis=1)


        month_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                     7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}


        all_months = list(range(1, 13))
        monthly_pivot = monthly_pivot.reindex(columns=all_months + ['Total'], fill_value=0)


        col_names = ['Year'] + [month_map[m] for m in all_months] + ['Total']
        self.div_tree["columns"] = col_names


        for col in col_names:
            self.div_tree.heading(col, text=col)
            self.div_tree.column(col, width=60, anchor='e')
        self.div_tree.column("Year", width=60, anchor='center')
        self.div_tree.column("Total", width=80, anchor='e')


        for year, row in monthly_pivot.iterrows():
            values = [year]
            for m in all_months:
                val = row[m]
                values.append(f"{val:,.2f}")
            values.append(f"{row['Total']:,.2f}")


            self.div_tree.insert("", "end", values=values)


    def _bt_error(self, msg):
        self.bt_text_output.insert(tk.END, f"\nERROR: {msg}")
        messagebox.showerror("Backtest Error", msg)
        self.btn_run_bt.config(state='normal')


    def create_optimization_tab(self):
        self.tab_opt = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_opt, text="Portfolio Optimization")


        input_frame = ttk.LabelFrame(self.tab_opt, text="Configuration", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)


        ttk.Label(input_frame, text="Tickers (comma sep):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.opt_tickers_entry = ttk.Entry(input_frame, width=50)
        self.opt_tickers_entry.grid(row=0, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.opt_tickers_entry.insert(0, "PETR4, UNIP6, CMIG4, BBAS3, BBSE3, ITUB4, CXSE3, SLCE3")


        ttk.Label(input_frame, text="Start Date:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.opt_start_entry = ttk.Entry(input_frame, width=15)
        self.opt_start_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.opt_start_entry.insert(0, "2010-01-01")


        self.btn_import_bt = ttk.Button(input_frame, text="Import from Backtest", command=self.import_tickers_from_bt)
        self.btn_import_bt.grid(row=0, column=3, sticky='w', padx=5, pady=5)


        self.btn_run_opt = ttk.Button(input_frame, text="Optimize Portfolio", command=self.run_optimization_thread)
        self.btn_run_opt.grid(row=1, column=3, sticky='e', padx=5, pady=5)


        self.opt_results_frame = ttk.LabelFrame(self.tab_opt, text="Results", padding=10)
        self.opt_results_frame.pack(fill='both', expand=True, padx=10, pady=10)


        self.opt_chart_notebook = ttk.Notebook(self.opt_results_frame)
        self.opt_chart_notebook.pack(side='left', fill='both', expand=True, padx=5)


        self.opt_frontier_tab = ttk.Frame(self.opt_chart_notebook)
        self.opt_chart_notebook.add(self.opt_frontier_tab, text="Efficient Frontier")


        self.opt_perf_tab = ttk.Frame(self.opt_chart_notebook)
        self.opt_chart_notebook.add(self.opt_perf_tab, text="Historical Performance")


        self.opt_weights_frame = ttk.Frame(self.opt_results_frame)
        self.opt_weights_frame.pack(side='right', fill='y', padx=5)


        columns = ("Stock", "Max Sharpe", "Min Vol", "Optimal")
        self.opt_tree = ttk.Treeview(self.opt_weights_frame, columns=columns, show='headings', height=15)
        for col in columns:
            self.opt_tree.heading(col, text=col)
            self.opt_tree.column(col, width=90, anchor='center')
        self.opt_tree.pack(fill='both', expand=True)


    def import_tickers_from_bt(self):
        bt_text = self.bt_tickers_entry.get()
        self.opt_tickers_entry.delete(0, tk.END)
        self.opt_tickers_entry.insert(0, bt_text)


    def run_optimization_thread(self):
        tickers_str = self.opt_tickers_entry.get()
        start_date = self.opt_start_entry.get()


        if not tickers_str or not start_date:
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return


        raw_tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        tickers = []
        for t in raw_tickers:
           tickers.append(t if ('.' in t or '=' in t) else f"{t}.SA")


        self.btn_run_opt.config(state='disabled')
        self.opt_tree.delete(*self.opt_tree.get_children())


        for widget in self.opt_frontier_tab.winfo_children(): widget.destroy()
        for widget in self.opt_perf_tab.winfo_children(): widget.destroy()


        lbl = ttk.Label(self.opt_frontier_tab, text="Optimizing... This may take a moment.")
        lbl.pack(pady=20)


        t = threading.Thread(target=self._process_optimization, args=(tickers, start_date))
        t.start()


    def _process_optimization(self, tickers, start_date):
        try:
            opt = optimization_tool.PortfolioOptimizer(tickers, start_date)


            sim_results, max_sharpe, min_vol, optimal = opt.optimize(num_portfolios=5000)


            self.after(0, lambda: self._show_optimization_results(sim_results, max_sharpe, min_vol, optimal))


        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Optimization Error", str(e)))
            self.after(0, lambda: self.btn_run_opt.config(state='normal'))


    def _show_optimization_results(self, sim_results, max_sharpe, min_vol, optimal):
        self.btn_run_opt.config(state='normal')


        self.opt_tree.delete(*self.opt_tree.get_children())
        tickers = max_sharpe['Weights'].keys()


        for t in tickers:
            w_sharpe = max_sharpe['Weights'].get(t, 0)
            w_vol = min_vol['Weights'].get(t, 0)
            w_opt = optimal['Weights'].get(t, 0)
            self.opt_tree.insert("", "end", values=(t, f"{w_sharpe:.2%}", f"{w_vol:.2%}", f"{w_opt:.2%}"))


        self.opt_tree.insert("", "end", values=("---", "---", "---", "---"))
        self.opt_tree.insert("", "end", values=("Return", f"{max_sharpe['Return']:.2%}", f"{min_vol['Return']:.2%}", f"{optimal['Return']:.2%}"))
        self.opt_tree.insert("", "end", values=("Volatility", f"{max_sharpe['Volatility']:.2%}", f"{min_vol['Volatility']:.2%}", f"{optimal['Volatility']:.2%}"))
        self.opt_tree.insert("", "end", values=("Sharpe", f"{max_sharpe['Sharpe']:.2f}", f"{min_vol['Sharpe']:.2f}", f"{optimal['Sharpe']:.2f}"))
        self.opt_tree.insert("", "end", values=("Max Drawdown", f"{max_sharpe['MaxDrawdown']:.2%}", f"{min_vol['MaxDrawdown']:.2%}", f"{optimal['MaxDrawdown']:.2%}"))


        for widget in self.opt_frontier_tab.winfo_children(): widget.destroy()


        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)


        sc = ax.scatter(sim_results[1,:], sim_results[0,:], c=sim_results[2,:], cmap='viridis', s=2, alpha=0.5)
        fig.colorbar(sc, ax=ax, label='Sharpe Ratio')


        ax.scatter(max_sharpe['Volatility'], max_sharpe['Return'], c='red', marker='*', s=150, label='Max Sharpe')
        ax.scatter(min_vol['Volatility'], min_vol['Return'], c='blue', marker='*', s=150, label='Min Volatility')
        ax.scatter(optimal['Volatility'], optimal['Return'], c='green', marker='*', s=150, label='Optimal (Best Combo)')


        ax.set_title("Efficient Frontier")
        ax.set_xlabel("Annual Volatility")
        ax.set_ylabel("Annual Return")
        ax.legend()
        ax.grid(True, alpha=0.3)


        fig.tight_layout()


        canvas = FigureCanvasTkAgg(fig, master=self.opt_frontier_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)


        for widget in self.opt_perf_tab.winfo_children(): widget.destroy()


        fig2 = Figure(figsize=(5, 4), dpi=100)
        ax2 = fig2.add_subplot(111)


        if 'EquityCurve' in max_sharpe:
            ax2.plot(max_sharpe['EquityCurve'].index, max_sharpe['EquityCurve'], label='Max Sharpe', color='red')
            ax2.plot(min_vol['EquityCurve'].index, min_vol['EquityCurve'], label='Min Volatility', color='blue')
            ax2.plot(optimal['EquityCurve'].index, optimal['EquityCurve'], label='Optimal', color='green')


        ax2.set_title("Historical Performance (Base 100)")
        ax2.set_ylabel("Portfolio Value")
        ax2.legend()
        ax2.grid(True)


        fig2.tight_layout()


        canvas2 = FigureCanvasTkAgg(fig2, master=self.opt_perf_tab)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill='both', expand=True)


        canvas2.get_tk_widget().pack(fill='both', expand=True)


    def create_breadth_tab(self):
        self.tab_breadth = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_breadth, text="Market Breadth (Ibovespa)")


        ctrl_frame = ttk.LabelFrame(self.tab_breadth, text="Controls", padding=10)
        ctrl_frame.pack(fill='x', padx=10, pady=10)


        ttk.Label(ctrl_frame, text="Analyze stocks above Moving Averages (Fear & Greed Proxy)").pack(side='left', padx=10)


        self.var_full_market = tk.BooleanVar(value=False)
        self.chk_full = ttk.Checkbutton(ctrl_frame, text="Scan Full B3 Market (Slower)", variable=self.var_full_market)
        self.chk_full.pack(side='left', padx=10)


        self.btn_run_breadth = ttk.Button(ctrl_frame, text="Run Analysis", command=self.run_breadth_thread)
        self.btn_run_breadth.pack(side='right', padx=10)


        self.breadth_results_frame = ttk.Frame(self.tab_breadth)
        self.breadth_results_frame.pack(fill='both', expand=True, padx=10, pady=10)


        self.breadth_chart_frame = ttk.LabelFrame(self.breadth_results_frame, text="Breadth Chart")
        self.breadth_chart_frame.pack(side='left', fill='both', expand=True, padx=5)


        self.breadth_info_frame = ttk.LabelFrame(self.breadth_results_frame, text="Interpretation", width=300)
        self.breadth_info_frame.pack(side='right', fill='y', padx=5)


        self.breadth_text = tk.Text(self.breadth_info_frame, width=40, height=20, wrap='word')
        self.breadth_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.breadth_text.insert(tk.END, "Click 'Run Analysis' to see data.\n\n")
        self.breadth_text.insert(tk.END, "Interpretation:\n")
        self.breadth_text.insert(tk.END, "- > 80% Above MA200: Extreme Greed (Risk of correction)\n")
        self.breadth_text.insert(tk.END, "- < 20% Above MA200: Extreme Fear (Potential bottom)\n")


    def run_breadth_thread(self):
        self.btn_run_breadth.config(state='disabled')
        mode_text = "Full Market (Scraping Fundamentus...)" if self.var_full_market.get() else "~56 Ibovespa stocks"
        self.breadth_text.delete("1.0", tk.END)
        self.breadth_text.insert(tk.END, f"Fetching data for {mode_text}...\nThis may take a minute...")


        for widget in self.breadth_chart_frame.winfo_children(): widget.destroy()


        mode = 'full' if self.var_full_market.get() else 'default'
        t = threading.Thread(target=self._process_breadth, args=(mode,))
        t.start()


    def _process_breadth(self, mode):
        try:
            analyzer = market_breadth.BreadthAnalyzer(mode=mode)
            metrics, details = analyzer.calculate_breadth()


            self.after(0, lambda: self._show_breadth_results(metrics))


        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Breadth Error", str(e)))
            self.after(0, lambda: self.btn_run_breadth.config(state='normal'))


    def _show_breadth_results(self, metrics):
        self.btn_run_breadth.config(state='normal')
        if not metrics:
            self.breadth_text.insert(tk.END, "\nNo data returned.")
            return


        self.breadth_text.delete("1.0", tk.END)
        self.breadth_text.insert(tk.END, "=== Market Breadth ===\n\n")


        for ma, pct in metrics.items():
            self.breadth_text.insert(tk.END, f"{ma}: {pct:.1%} of stocks above average\n")


        pct200 = metrics.get('MA200', 0)
        status = "Neutral"
        if pct200 > 0.80: status = "EXTREME GREED"
        elif pct200 > 0.60: status = "Greed"
        elif pct200 < 0.20: status = "EXTREME FEAR"
        elif pct200 < 0.40: status = "Fear"


        self.breadth_text.insert(tk.END, f"\nSentiment (MA200): {status}\n")


        for widget in self.breadth_chart_frame.winfo_children(): widget.destroy()


        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)


        mas = list(metrics.keys())


        vals = [metrics[k]*100 for k in mas]


        colors = ['red' if '200' in m else 'skyblue' for m in mas]
        bars = ax.bar(mas, vals, color=colors)


        ax.set_ylim(0, 100)
        ax.set_ylabel("% Stocks Above MA")
        ax.set_title("Ibovespa Market Breadth")
        ax.axhline(50, color='gray', linestyle='--', alpha=0.5)
        ax.axhline(80, color='red', linestyle=':', alpha=0.5, label='Overbought')
        ax.axhline(20, color='green', linestyle=':', alpha=0.5, label='Oversold')


        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom')


        fig.tight_layout()


        canvas = FigureCanvasTkAgg(fig, master=self.breadth_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)


    def create_rrg_tab(self):
        self.tab_rrg = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_rrg, text="RRG Analysis")


        input_frame = ttk.LabelFrame(self.tab_rrg, text="Configuration", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)


        ttk.Label(input_frame, text="Tickers (comma sep):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.rrg_tickers_entry = ttk.Entry(input_frame, width=50)
        self.rrg_tickers_entry.grid(row=0, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.rrg_tickers_entry.insert(0, "VALE3, PETR4, ITUB4, BBDC4, AXIA3, BBAS3, BPAC11")


        self.btn_import_bt_rrg = ttk.Button(input_frame, text="Import from Backtest", command=self.import_tickers_from_bt_to_rrg)
        self.btn_import_bt_rrg.grid(row=0, column=3, sticky='w', padx=5, pady=5)


        ttk.Label(input_frame, text="Benchmark:").grid(row=0, column=4, sticky='w', padx=5, pady=5)
        self.rrg_bench_entry = ttk.Entry(input_frame, width=15)
        self.rrg_bench_entry.grid(row=0, column=5, sticky='w', padx=5, pady=5)
        self.rrg_bench_entry.insert(0, "^BVSP")


        ttk.Label(input_frame, text="Window (Days):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.rrg_window_entry = ttk.Entry(input_frame, width=10)
        self.rrg_window_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.rrg_window_entry.insert(0, "60")


        ttk.Label(input_frame, text="Trail Length:").grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.rrg_trail_entry = ttk.Entry(input_frame, width=10)
        self.rrg_trail_entry.grid(row=1, column=3, sticky='w', padx=5, pady=5)
        self.rrg_trail_entry.insert(0, "10")


        self.btn_run_rrg = ttk.Button(input_frame, text="Run RRG", command=self.run_rrg_thread)
        self.btn_run_rrg.grid(row=1, column=5, sticky='e', padx=5, pady=5)


        self.rrg_chart_frame = ttk.LabelFrame(self.tab_rrg, text="Relative Rotation Graph", padding=10)
        self.rrg_chart_frame.pack(fill='both', expand=True, padx=10, pady=10)


        self.rrg_status_label = ttk.Label(self.rrg_chart_frame, text="Click 'Run RRG' to start (this requires downloading data).")
        self.rrg_status_label.pack(pady=5)


    def import_tickers_from_bt_to_rrg(self):
        bt_text = self.bt_tickers_entry.get()
        self.rrg_tickers_entry.delete(0, tk.END)
        self.rrg_tickers_entry.insert(0, bt_text)


    def run_rrg_thread(self):
        tickers_str = self.rrg_tickers_entry.get()
        bench = self.rrg_bench_entry.get().strip().upper()


        if not tickers_str or not bench:
             messagebox.showwarning("Input Error", "Please provide tickers and benchmark.")
             return


        try:
             window = int(self.rrg_window_entry.get())
             trail = int(self.rrg_trail_entry.get())
        except ValueError:
             messagebox.showerror("Input Error", "Window and Trail must be integers.")
             return


        raw_tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]


        tickers = []
        for t in raw_tickers:
            tickers.append(t if ('.' in t or '=' in t) else f"{t}.SA")


        self.btn_run_rrg.config(state='disabled')
        self.rrg_status_label.config(text="Fetching data and calculating... Please wait.")


        for widget in self.rrg_chart_frame.winfo_children():
            if widget != self.rrg_status_label: widget.destroy()


        t = threading.Thread(target=self._process_rrg, args=(tickers, bench, window, trail))
        t.start()


    def _process_rrg(self, tickers, bench, window, trail):
        try:


            start_date = "2023-01-01"


            rrg = rrg_tool.RRGCalculator(tickers, bench, start_date, window)
            rrg.calculate()


            trails_data = rrg.get_trails(trail)
            latest_data = rrg.get_latest_values()


            self.after(0, lambda: self._show_rrg_results(trails_data, latest_data))


        except Exception as e:
            self.after(0, lambda: messagebox.showerror("RRG Error", str(e)))
            self.after(0, lambda: self.btn_run_rrg.config(state='normal'))
            self.after(0, lambda: self.rrg_status_label.config(text="Error occurred."))


    def _show_rrg_results(self, trails, latest):
        self.btn_run_rrg.config(state='normal')
        self.rrg_status_label.config(text=f"RRG Generated. {len(latest)} assets.")


        for widget in self.rrg_chart_frame.winfo_children():
            if widget != self.rrg_status_label: widget.destroy()


        fig = Figure(figsize=(6, 6), dpi=100)
        ax = fig.add_subplot(111)


        ax.axhline(100, color='gray', linestyle='-', alpha=0.5)
        ax.axvline(100, color='gray', linestyle='-', alpha=0.5)


        max_dist = 0
        for ticker, df in trails.items():
            if ticker in latest:


                r_max = abs(df['RS_Ratio'] - 100).max()
                m_max = abs(df['RS_Momentum'] - 100).max()
                max_dist = max(max_dist, r_max, m_max)


        limit = max_dist + 2
        if limit < 2: limit = 2


        ax.set_xlim(100 - limit, 100 + limit)
        ax.set_ylim(100 - limit, 100 + limit)


        ax.text(0.95, 0.95, "LEADING", transform=ax.transAxes,
                color='green', fontweight='bold', alpha=0.3, ha='right', va='top')


        ax.text(0.95, 0.05, "WEAKENING", transform=ax.transAxes,
                color='orange', fontweight='bold', alpha=0.3, ha='right', va='bottom')


        ax.text(0.05, 0.05, "LAGGING", transform=ax.transAxes,
                color='red', fontweight='bold', alpha=0.3, ha='left', va='bottom')


        ax.text(0.05, 0.95, "IMPROVING", transform=ax.transAxes,
                color='blue', fontweight='bold', alpha=0.3, ha='left', va='top')


        for ticker, df in trails.items():
            if ticker in latest:


                ax.plot(df['RS_Ratio'], df['RS_Momentum'],  alpha=0.6, linewidth=1)


                ratio = latest[ticker]['RS_Ratio']
                mom = latest[ticker]['RS_Momentum']


                color = 'black'
                if ratio > 100 and mom > 100: color = 'green'
                elif ratio > 100 and mom < 100: color = 'orange'
                elif ratio < 100 and mom < 100: color = 'red'
                elif ratio < 100 and mom > 100: color = 'blue'


                ax.scatter(ratio, mom, color=color, s=50)
                ax.text(ratio, mom, f" {ticker}", fontsize=8)


        ax.set_title("Relative Rotation Graph (vs Benchmark)")
        ax.set_xlabel("JdK RS-Ratio (Trend)")
        ax.set_ylabel("JdK RS-Momentum (Velocity)")
        ax.grid(True, linestyle=':', alpha=0.6)


        fig.tight_layout()


        canvas = FigureCanvasTkAgg(fig, master=self.rrg_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)


if __name__ == "__main__":
    app = FinancialDashboardArgs()
    app.mainloop()
