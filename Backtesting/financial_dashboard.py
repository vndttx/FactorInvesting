from datetime import datetime
import pandas as pd
import numpy as np
import yfinance as yf
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import threading
import matplotlib
import matplotlib.pyplot as plt
import valuation
import backtest_tool
import optimization_tool
import market_breadth
import rrg_tool
import fund_tool
from matplotlib.figure import Figure
import matplotlib.ticker as mtick

GLOBAL_DATA_CACHE = {}

def get_cached_data(tickers, start_date, end_date):
    """Recupera dados do yfinance com cache para evitar downloads redundantes."""
    # Criamos uma chave única baseada nos tickers e no período
    cache_key = (tuple(sorted(tickers)), start_date, end_date)
    
    if cache_key not in GLOBAL_DATA_CACHE:
        print(f"Baixando novos dados para: {tickers}")
        # Baixamos com actions=True para garantir Dividendos e Splits
        data = yf.download(tickers, start=start_date, end=end_date, actions=True)
        GLOBAL_DATA_CACHE[cache_key] = data
    else:
        print(f"Usando dados em cache para: {tickers}")
        
    return GLOBAL_DATA_CACHE[cache_key]

plt.style.use('dark_background')
matplotlib.rcParams.update({
    "figure.facecolor": "#121212",
    "axes.facecolor": "#121212",
    "axes.edgecolor": "#1a1a1a",
    "grid.color": "#252525",
    "text.color": "#e0e0e0",
    "axes.labelcolor": "#e0e0e0",
    "axes.labelweight": "bold",
    "xtick.color": "#9e9e9e",
    "ytick.color": "#9e9e9e",
    "patch.edgecolor": "#121212",
    "figure.autolayout": True,
    "axes.spines.top": False,
    "axes.spines.right": False
})

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
except ImportError as e:
    messagebox.showerror("Matplotlib Error", 
        f"Could not find the Matplotlib TkAgg backend.\n\n"
        f"Error: {e}\n\n"
        "To fix this, please run the following command in your terminal:\n"
        "pip install matplotlib --upgrade --force-reinstall")
    sys.exit(1)


class FinancialDashboardArgs(tk.Tk):
    def et_cached_datag(self, tickers, start, end):
        cache_key = (tuple(sorted(tickers)), start_date, end_date)
        if cache_key not in GLOBAL_DATA_CACHE:
         print(f"Baixando novos dados para: {tickers}")
         data = yf.download(tickers, start=start_date, end=end_date, actions=True)
         GLOBAL_DATA_CACHE[cache_key] = data
        else:
         print(f"Usando dados em cache para: {tickers}")
        
        return GLOBAL_DATA_CACHE[cache_key]
    
    def __init__(self):
        super().__init__()
        self.is_processing = False
        self.progress_var = tk.DoubleVar()
        self.title("Factor Investing Dashboard")
        self.geometry("900x720")
        self.configure(bg="#121212")
        self._setup_dark_theme()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        self.create_valuation_tab()
        self.create_backtest_tab()
        self.create_optimization_tab()
        self.create_breadth_tab()
        self.create_rrg_tab()
        status_frame = tk.Frame(self, height=150, bg="#121212")
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=2)
        self.log_console = tk.Text(status_frame, height=6, state='disabled', bg="#1a1a1a", 
                                   fg="#d4d4d4", font=("Consolas", 9), borderwidth=0)
        self.log_console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(status_frame, command=self.log_console.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_console.config(yscrollcommand=scrollbar.set)

    def _setup_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg, fg, accent, highlight, select = "#121212", "#e0e0e0", "#1e1e1e", "#252525", "#0078d7"

        style.configure(".", background=bg, foreground=fg, fieldforeground=fg, font=('Segoe UI', 10), borderwidth=0, highlightthickness=0)
        
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=accent, foreground="#999999", padding=[22, 10], borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", select)], foreground=[("selected", fg)])
        style.configure("TFrame", background=bg, borderwidth=0)
        style.configure("TLabelframe", background=bg, foreground=select, borderwidth=0)
        style.configure("TLabelframe.Label", background=bg, foreground=select, font=('Segoe UI', 10, 'bold'), padding=8)
        style.configure("TLabel", background=bg, foreground=fg)
        
        style.configure("Treeview", background="#1a1a1a", foreground=fg, fieldbackground="#1a1a1a", borderwidth=0, rowheight=34)
        style.map("Treeview", background=[("selected", select)], foreground=[("selected", fg)])
        style.configure("Treeview.Heading", background=highlight, foreground=fg, borderwidth=0, relief="flat", font=('Segoe UI', 9, 'bold'), padding=8)
        style.map("Treeview.Heading", background=[("active", "#3d3d3d")])

        style.configure("TButton", background=accent, foreground=fg, borderwidth=0, padding=10, relief="flat")
        style.map("TButton", background=[("active", highlight)])
        
        style.configure("TEntry", fieldbackground="#1a1a1a", foreground=fg, borderwidth=0, relief="flat")
        style.map("TCheckbutton", background=[("active", bg)])

    @staticmethod
    def _format_ticker(ticker):
        t = ticker.strip().upper()
        if not t: return None
        return t if ('.' in t or '=' in t) else f"{t}.SA"

    def _format_tickers(self, tickers_str):
        return [self._format_ticker(t) for t in tickers_str.split(',') if t.strip()]

    def _run_in_thread(self, target, args=()):
        t = threading.Thread(target=target, args=args, daemon=True)
        t.start()
        
    def log(self, message, level="INFO"):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] [{level}] {message}\n"
        
        self.log_console.config(state='normal')
        self.log_console.insert(tk.END, full_message)
        self.log_console.see(tk.END)
        self.log_console.config(state='disabled')
        self.update_idletasks()

    def _clear_frame(self, frame, exclude=None):
        for widget in frame.winfo_children():
            if exclude and widget == exclude: continue
            widget.destroy()

    def create_valuation_tab(self):
        self.tab_val = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_val, text="Stock Valuation")

        input_frame = ttk.LabelFrame(self.tab_val, text="Input", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)

        ttk.Label(input_frame, text="Ticker (e.g., BBAS3):").pack(side='left', padx=5)
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

    def _add_labeled_entry(self, parent, label_text, row, col, width=15, default_val="", columnspan=1):
        ttk.Label(parent, text=label_text).grid(row=row, column=col, sticky='w', padx=5, pady=5)
        entry = ttk.Entry(parent, width=width)
        entry.grid(row=row, column=col+1, columnspan=columnspan, sticky='w', padx=5, pady=5)
        entry.insert(0, default_val)
        return entry

    def create_backtest_tab(self):
        self.tab_bt = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bt, text="Portfolio Backtest")

        # Configuration Section
        input_frame = ttk.LabelFrame(self.tab_bt, text="Configuration", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)

        self.bt_tickers_entry = self._add_labeled_entry(input_frame, "Tickers (comma sep):", 0, 0, 50, "BBAS3, BBSE3, CMIG4, CXSE3", 3)
        self.bt_initial_entry = self._add_labeled_entry(input_frame, "Initial Invest (BRL):", 1, 0, 15, "1000")
        self.bt_monthly_entry = self._add_labeled_entry(input_frame, "Monthly Invest (BRL):", 1, 2, 15, "600")
        self.bt_start_entry   = self._add_labeled_entry(input_frame, "Start Date (YYYY-MM-DD):", 2, 0, 15, "2015-01-01")
        self.bt_rf_alloc_entry = self._add_labeled_entry(input_frame, "Risk Free Alloc (%):", 2, 2, 15, "0")

        self.btn_run_bt = ttk.Button(input_frame, text="Run Backtest", command=self.run_backtest_thread)
        self.btn_run_bt.grid(row=3, column=3, sticky='e', padx=5, pady=5)

        # Results Section
        self.bt_results_frame = ttk.LabelFrame(self.tab_bt, text="Performance Outcomes", padding=10)
        self.bt_results_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.bt_notebook = ttk.Notebook(self.bt_results_frame)
        self.bt_notebook.pack(fill='both', expand=True)

        # Summary & Chart Tab
        self.bt_tab_summary = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(self.bt_tab_summary, text="Summary & Chart")

        self.bt_text_output = tk.Text(self.bt_tab_summary, height=10, width=50, 
                                     bg="#1a1a1a", fg="#e0e0e0", insertbackground="white", 
                                     borderwidth=0, relief="flat", font=("Consolas", 10), padx=8, pady=8)
        self.bt_text_output.pack(side='left', fill='y', padx=5, pady=5)

        self.bt_chart_frame = ttk.Frame(self.bt_tab_summary)
        self.bt_chart_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # Dividends Tab
        self.bt_tab_divs = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(self.bt_tab_divs, text="Monthly Dividends")

        self.div_tree = ttk.Treeview(self.bt_tab_divs, show='headings')
        self.div_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        # Scrollbars
        vsb = ttk.Scrollbar(self.bt_tab_divs, orient="vertical", command=self.div_tree.yview)
        vsb.pack(side='right', fill='y')
        hsb = ttk.Scrollbar(self.bt_tab_divs, orient="horizontal", command=self.div_tree.xview)
        hsb.pack(side='bottom', fill='x')
        self.div_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    def run_valuation(self):
        ticker = self._format_ticker(self.val_ticker_entry.get())
        if not ticker:
            messagebox.showwarning("Input Error", "Please enter a ticker symbol.")
            return

        self.val_status_label.config(text=f"Fetching data for {ticker}...")
        self.val_tree.delete(*self.val_tree.get_children())
        self.update_idletasks()
        self._run_in_thread(self._process_valuation, args=(ticker,))

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

            pe, eps = data.get('pe_ratio'), data.get('eps')
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
            error_msg = str(e)  # Captura a mensagem antes do bloco fechar
            self.after(0, lambda msg=error_message: messagebox.showerror("Error", msg))

    def _update_val_table(self, rows, current_price):
        for row in rows:
            self.val_tree.insert("", "end", values=row)
        self.val_status_label.config(text=f"Analysis complete. Current Price: R$ {current_price:.2f}")

    def run_backtest_thread(self):
        if self.is_processing:
            self.log("Aguarde o término do processo atual.", "WARNING")
            return
        tickers = self._format_tickers(self.bt_tickers_entry.get())
        init_str, monthly_str = self.bt_initial_entry.get(), self.bt_monthly_entry.get()
        start_date, rf_alloc_str = self.bt_start_entry.get(), self.bt_rf_alloc_entry.get()

        if not (tickers and init_str and monthly_str and start_date and rf_alloc_str):
            messagebox.showwarning("Missing Inputs", "Please fill all fields.")
            return

        try:
            initial, monthly = float(init_str), float(monthly_str)
            rf_alloc = float(rf_alloc_str)
            if not (0 <= rf_alloc <= 100):
                 messagebox.showerror("Invalid Input", "Risk Free Allocation must be between 0 and 100.")
                 return
            rf_alloc_decimal = rf_alloc / 100.0
        except ValueError:
            messagebox.showerror("Invalid Number", "Investments/Allocation must be numbers.")
            return

        self.btn_run_bt.config(state='disabled')
        self.is_processing = True # ATIVA FLAG
        self.progress_var.set(10)
        self.log(f"Iniciando Backtest para: {self.bt_tickers_entry.get()}")
        self._run_in_thread(self._process_backtest, args=(tickers, initial, monthly, start_date, rf_alloc_decimal))

    def _process_backtest(self, tickers, initial, monthly, start_date, rf_alloc_decimal):
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            price_div_data = get_cached_data(tickers, start_date, end_date)     
                   
            bt = backtest_tool.PortfolioBacktester(
            tickers, initial, monthly, start_date, 
            risk_free_allocation=rf_alloc_decimal,
            injected_data=price_div_data)
            bt.run()
            self.progress_var.set(50)
            self.progress_var.set(100)
            self.log("Backtest concluído com sucesso.")

            m_reinvest = bt.calculate_metrics(bt.daily_returns_reinvest, bt.risk_free_daily_series.values)
            m_no_reinvest = bt.calculate_metrics(bt.daily_returns_no_reinvest, bt.risk_free_daily_series.values)

            m_reinvest["Beta (vs Ibov)"] = bt.calculate_beta(bt.daily_returns_reinvest)
            m_no_reinvest["Beta (vs Ibov)"] = bt.calculate_beta(bt.daily_returns_no_reinvest)

            output = ["\n=== PERFORMANCE METRICS ===\n", f"{'Metric':<25} | {'With Reinvest':<15} | {'No Reinvest':<15}", "-" * 65]
            for k in m_reinvest.keys():
                val_r, val_nr = m_reinvest[k], m_no_reinvest[k]
                if k in ["Total Return", "CAGR", "Volatility", "Max Drawdown"]:
                    fmt_r, fmt_nr = f"{val_r*100:.2f}%", f"{val_nr*100:.2f}%"
                else:
                    fmt_r, fmt_nr = f"{val_r:.2f}", f"{val_nr:.2f}"
                output.append(f"{k:<25} | {fmt_r:<15} | {fmt_nr:<15}")

            output.append("\n\n=== FINAL PORTFOLIO VALUES (BRL) ===")
            final = bt.results.iloc[-1]
            for k, v in final.items():
                output.append(f"{k:<25}: R$ {v:,.2f}")

            self.after(0, lambda: self._show_bt_results("\n".join(output), bt))
        except Exception as e:
            self.log(f"Erro: {str(e)}", "ERROR")
            self._bt_error(str(e))
        finally:
            self.is_processing = False
            self.btn_run_bt.config(state='normal')
            self.after(2000, lambda: self.progress_var.set(0))

    def _show_bt_results(self, report, bt_obj):
        self.bt_text_output.delete("1.0", tk.END)
        self.bt_text_output.insert(tk.END, report)
        self.btn_run_bt.config(state='normal')
        self._clear_frame(self.bt_chart_frame)

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
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')))
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.bt_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self._populate_div_table(bt_obj)

    def _populate_div_table(self, bt_obj):
        self.div_tree.delete(*self.div_tree.get_children())
        self.div_tree["columns"] = []
        if not bt_obj.daily_dividends: return

        df_divs = pd.DataFrame.from_dict(bt_obj.daily_dividends, orient='index', columns=['Dividend'])
        df_divs.index = pd.to_datetime(df_divs.index)
        monthly_pivot = df_divs.pivot_table(index=df_divs.index.year, columns=df_divs.index.month, values='Dividend', aggfunc='sum').fillna(0)
        monthly_pivot['Total'] = monthly_pivot.sum(axis=1)
        
        all_months = list(range(1, 13))
        month_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
        monthly_pivot = monthly_pivot.reindex(columns=all_months + ['Total'], fill_value=0)

        col_names = ['Year'] + [month_map[m] for m in all_months] + ['Total']
        self.div_tree["columns"] = col_names
        for col in col_names:
            self.div_tree.heading(col, text=col)
            self.div_tree.column(col, width=60, anchor='e')
        self.div_tree.column("Year", width=60, anchor='center')
        self.div_tree.column("Total", width=80, anchor='e')

        for year, row in monthly_pivot.iterrows():
            values = [year] + [f"{row[m]:,.2f}" for m in all_months] + [f"{row['Total']:,.2f}"]
            self.div_tree.insert("", "end", values=values)

    def update_plot(self, figure):
    # Em vez de criar um novo FigureCanvasTkAgg toda vez:
        if hasattr(self, 'canvas_widget'):
            self.canvas_widget.get_tk_widget().destroy()
            self.is_processing = False
            self.canvas_widget = FigureCanvasTkAgg(figure, master=self.plot_frame)
            self.canvas_widget.draw()
            self.canvas_widget.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
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

        ttk.Button(input_frame, text="Import from Backtest", command=self.import_tickers_from_bt).grid(row=0, column=3, sticky='w', padx=5, pady=5)
        self.btn_run_opt = ttk.Button(input_frame, text="Optimize Portfolio", command=self.run_optimization_thread)
        self.btn_run_opt.grid(row=1, column=3, sticky='e', padx=5, pady=5)

        self.opt_results_frame = ttk.LabelFrame(self.tab_opt, text="Results", padding=10)
        self.opt_results_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.opt_chart_notebook = ttk.Notebook(self.opt_results_frame)
        self.opt_chart_notebook.pack(side='left', fill='both', expand=True, padx=5)

        self.opt_frontier_tab, self.opt_perf_tab = ttk.Frame(self.opt_chart_notebook), ttk.Frame(self.opt_chart_notebook)
        self.opt_chart_notebook.add(self.opt_frontier_tab, text="Efficient Frontier")
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
        self.opt_tickers_entry.delete(0, tk.END)
        self.opt_tickers_entry.insert(0, self.bt_tickers_entry.get())

    def run_optimization_thread(self):
        tickers = self._format_tickers(self.opt_tickers_entry.get())
        start_date = self.opt_start_entry.get()
        if not (tickers and start_date):
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return

        self.btn_run_opt.config(state='disabled')
        self.opt_tree.delete(*self.opt_tree.get_children())
        self._clear_frame(self.opt_frontier_tab)
        self._clear_frame(self.opt_perf_tab)

        ttk.Label(self.opt_frontier_tab, text="Optimizing... This may take a moment.").pack(pady=20)
        self._run_in_thread(self._process_optimization, args=(tickers, start_date))

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
        for t in max_sharpe['Weights'].keys():
            self.opt_tree.insert("", "end", values=(t, f"{max_sharpe['Weights'].get(t, 0):.2%}", f"{min_vol['Weights'].get(t, 0):.2%}", f"{optimal['Weights'].get(t, 0):.2%}"))

        self.opt_tree.insert("", "end", values=("---", "---", "---", "---"))
        for k, fmt in [('Return', '.2%'), ('Volatility', '.2%'), ('Sharpe', '.2f'), ('Max Drawdown', '.2%')]:
            self.opt_tree.insert("", "end", values=(k, f"{max_sharpe[k.replace(' ', '')]:{fmt}}", f"{min_vol[k.replace(' ', '')]:{fmt}}", f"{optimal[k.replace(' ', '')]:{fmt}}"))

        self._clear_frame(self.opt_frontier_tab)
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)
        sc = ax.scatter(sim_results[1,:], sim_results[0,:], c=sim_results[2,:], cmap='viridis', s=2, alpha=0.5)
        fig.colorbar(sc, ax=ax, label='Sharpe Ratio')
        ax.scatter(max_sharpe['Volatility'], max_sharpe['Return'], c='red', marker='*', s=150, label='Max Sharpe')
        ax.scatter(min_vol['Volatility'], min_vol['Return'], c='blue', marker='*', s=150, label='Min Volatility')
        ax.scatter(optimal['Volatility'], optimal['Return'], c='green', marker='*', s=150, label='Optimal')
        ax.set_title("Efficient Frontier"); ax.set_xlabel("Annual Volatility"); ax.set_ylabel("Annual Return"); ax.legend(); ax.grid(True, alpha=0.3)
        fig.tight_layout()
        FigureCanvasTkAgg(fig, master=self.opt_frontier_tab).get_tk_widget().pack(fill='both', expand=True)

        self._clear_frame(self.opt_perf_tab)
        fig2 = Figure(figsize=(5, 4), dpi=100); ax2 = fig2.add_subplot(111)
        if 'EquityCurve' in max_sharpe:
            for label, data, color in [('Max Sharpe', max_sharpe, 'red'), ('Min Volatility', min_vol, 'blue'), ('Optimal', optimal, 'green')]:
                ax2.plot(data['EquityCurve'].index, data['EquityCurve'], label=label, color=color)
        ax2.set_title("Historical Performance (Base 100)"); ax2.set_ylabel("Portfolio Value"); ax2.legend(); ax2.grid(True)
        fig2.tight_layout()
        FigureCanvasTkAgg(fig2, master=self.opt_perf_tab).get_tk_widget().pack(fill='both', expand=True)

    def create_breadth_tab(self):
        self.tab_breadth = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_breadth, text="Market Breadth (Ibovespa)")
        ctrl_frame = ttk.LabelFrame(self.tab_breadth, text="Controls", padding=10)
        ctrl_frame.pack(fill='x', padx=10, pady=10)
        ttk.Label(ctrl_frame, text="Analyze stocks above Moving Averages (Fear & Greed Proxy)").pack(side='left', padx=10)
        self.var_full_market = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_frame, text="Scan Full B3 Market (Slower)", variable=self.var_full_market).pack(side='left', padx=10)
        self.btn_run_breadth = ttk.Button(ctrl_frame, text="Run Analysis", command=self.run_breadth_thread)
        self.btn_run_breadth.pack(side='right', padx=10)
        
        results_frame = ttk.Frame(self.tab_breadth); results_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.breadth_chart_frame = ttk.LabelFrame(results_frame, text="Breadth Chart"); self.breadth_chart_frame.pack(side='left', fill='both', expand=True, padx=5)
        info_frame = ttk.LabelFrame(results_frame, text="Interpretation", width=300); info_frame.pack(side='right', fill='y', padx=5)
        self.breadth_text = tk.Text(info_frame, width=40, height=20, wrap='word', 
                                   bg="#333333", fg="#ffffff", insertbackground="white",
                                   borderwidth=0, relief="flat", font=("Segoe UI", 10), padx=5, pady=5)
        self.breadth_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.breadth_text.insert(tk.END, "Click 'Run Analysis' to see data.\n\nInterpretation:\n- > 80% Above MA200: Extreme Greed\n- < 20% Above MA200: Extreme Fear\n")

    def run_breadth_thread(self):
        self.btn_run_breadth.config(state='disabled')
        mode = 'full' if self.var_full_market.get() else 'default'
        mode_text = "Full Market" if mode == 'full' else "~56 Ibovespa stocks"
        self.breadth_text.delete("1.0", tk.END); self.breadth_text.insert(tk.END, f"Fetching data for {mode_text}...")
        self._clear_frame(self.breadth_chart_frame)
        self._run_in_thread(self._process_breadth, args=(mode,))

    def _process_breadth(self, mode):
        try:
            metrics, _ = market_breadth.BreadthAnalyzer(mode=mode).calculate_breadth()
            self.after(0, lambda: self._show_breadth_results(metrics))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Breadth Error", str(e)))
            self.after(0, lambda: self.btn_run_breadth.config(state='normal'))

    def _show_breadth_results(self, metrics):
        self.btn_run_breadth.config(state='normal')
        if not metrics: return
        self.breadth_text.delete("1.0", tk.END); self.breadth_text.insert(tk.END, "=== Market Breadth ===\n\n")
        for ma, pct in metrics.items(): self.breadth_text.insert(tk.END, f"{ma}: {pct:.1%} of stocks above average\n")
        pct200 = metrics.get('MA200', 0)
        status = "EXTREME GREED" if pct200 > 0.8 else "Greed" if pct200 > 0.6 else "EXTREME FEAR" if pct200 < 0.2 else "Fear" if pct200 < 0.4 else "Neutral"
        self.breadth_text.insert(tk.END, f"\nSentiment (MA200): {status}\n")

        self._clear_frame(self.breadth_chart_frame)
        fig = Figure(figsize=(5, 4), dpi=100); ax = fig.add_subplot(111); mas = list(metrics.keys())
        vals = [metrics[k]*100 for k in mas]
        bars = ax.bar(mas, vals, color=['red' if '200' in m else 'skyblue' for m in mas])
        ax.set_ylim(0, 100); ax.set_ylabel("% Stocks Above MA"); ax.set_title("Ibovespa Market Breadth")
        ax.axhline(50, color='gray', linestyle='--', alpha=0.5); ax.axhline(80, color='red', linestyle=':', alpha=0.5); ax.axhline(20, color='green', linestyle=':', alpha=0.5)
        for bar in bars: ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{bar.get_height():.1f}%', ha='center', va='bottom')
        fig.tight_layout()
        FigureCanvasTkAgg(fig, master=self.breadth_chart_frame).get_tk_widget().pack(fill='both', expand=True)

    def create_rrg_tab(self):
        self.tab_rrg = ttk.Frame(self.notebook); self.notebook.add(self.tab_rrg, text="RRG Analysis")
        input_frame = ttk.LabelFrame(self.tab_rrg, text="Configuration", padding=10); input_frame.pack(fill='x', padx=10, pady=10)
        ttk.Label(input_frame, text="Tickers (comma sep):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.rrg_tickers_entry = ttk.Entry(input_frame, width=50); self.rrg_tickers_entry.grid(row=0, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.rrg_tickers_entry.insert(0, "VALE3, PETR4, ITUB4, BBDC4, AXIA3, BBAS3, BPAC11")
        ttk.Button(input_frame, text="Import from Backtest", command=self.import_tickers_from_bt_to_rrg).grid(row=0, column=3, sticky='w', padx=5, pady=5)
        ttk.Label(input_frame, text="Benchmark:").grid(row=0, column=4, sticky='w', padx=5, pady=5)
        self.rrg_bench_entry = ttk.Entry(input_frame, width=15); self.rrg_bench_entry.grid(row=0, column=5, sticky='w', padx=5, pady=5); self.rrg_bench_entry.insert(0, "^BVSP")
        ttk.Label(input_frame, text="Window (Days):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.rrg_window_entry = ttk.Entry(input_frame, width=10); self.rrg_window_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5); self.rrg_window_entry.insert(0, "60")
        ttk.Label(input_frame, text="Trail Length:").grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.rrg_trail_entry = ttk.Entry(input_frame, width=10); self.rrg_trail_entry.grid(row=1, column=3, sticky='w', padx=5, pady=5); self.rrg_trail_entry.insert(0, "10")
        ttk.Button(input_frame, text="Run RRG", command=self.run_rrg_thread).grid(row=1, column=5, sticky='e', padx=5, pady=5)
        self.rrg_chart_frame = ttk.LabelFrame(self.tab_rrg, text="Relative Rotation Graph", padding=10); self.rrg_chart_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.rrg_status_label = ttk.Label(self.rrg_chart_frame, text="Click 'Run RRG' to start."); self.rrg_status_label.pack(pady=5)

    def import_tickers_from_bt_to_rrg(self):
        self.rrg_tickers_entry.delete(0, tk.END); self.rrg_tickers_entry.insert(0, self.bt_tickers_entry.get())

    def run_rrg_thread(self):
        tickers = self._format_tickers(self.rrg_tickers_entry.get())
        bench = self.rrg_bench_entry.get().strip().upper()
        if not (tickers and bench): messagebox.showwarning("Input Error", "Please provide tickers and benchmark."); return
        try:
             window, trail = int(self.rrg_window_entry.get()), int(self.rrg_trail_entry.get())
        except ValueError: messagebox.showerror("Input Error", "Window and Trail must be integers."); return
        self.btn_run_rrg = self.btn_run_rrg if hasattr(self, 'btn_run_rrg') else None # Safeguard
        self.rrg_status_label.config(text="Fetching data and calculating..."); self._clear_frame(self.rrg_chart_frame, exclude=self.rrg_status_label)
        self._run_in_thread(self._process_rrg, args=(tickers, bench, window, trail))

    def _process_rrg(self, tickers, bench, window, trail):
        try:
            rrg = rrg_tool.RRGCalculator(tickers, bench, "2023-01-01", window); rrg.calculate()
            self.after(0, lambda: self._show_rrg_results(rrg.get_trails(trail), rrg.get_latest_values()))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("RRG Error", str(e)))
            self.after(0, lambda: self.rrg_status_label.config(text="Error occurred."))

    def _show_rrg_results(self, trails, latest):
        self.rrg_status_label.config(text=f"RRG Generated. {len(latest)} assets.")
        self._clear_frame(self.rrg_chart_frame, exclude=self.rrg_status_label)
        fig = Figure(figsize=(6, 6), dpi=100); ax = fig.add_subplot(111)
        ax.axhline(100, color='gray', alpha=0.5); ax.axvline(100, color='gray', alpha=0.5)
        max_dist = max([max(abs(df['RS_Ratio'] - 100).max(), abs(df['RS_Momentum'] - 100).max()) for ticker, df in trails.items() if ticker in latest] + [2])
        limit = max_dist + 1; ax.set_xlim(100 - limit, 100 + limit); ax.set_ylim(100 - limit, 100 + limit)
        for t, x, y, c in [("LEADING", 0.95, 0.95, 'green'), ("WEAKENING", 0.95, 0.05, 'orange'), ("LAGGING", 0.05, 0.05, 'red'), ("IMPROVING", 0.05, 0.95, 'blue')]:
            ax.text(x, y, t, transform=ax.transAxes, color=c, fontweight='bold', alpha=0.2, ha='right' if x > 0.5 else 'left', va='top' if y > 0.5 else 'bottom')
        for ticker, df in trails.items():
            if ticker in latest:
                ax.plot(df['RS_Ratio'], df['RS_Momentum'], alpha=0.6, linewidth=1)
                r, m = latest[ticker]['RS_Ratio'], latest[ticker]['RS_Momentum']
                color = 'green' if r > 100 and m > 100 else 'orange' if r > 100 else 'red' if m < 100 else 'blue'
                ax.scatter(r, m, color=color, s=50); ax.text(r, m, f" {ticker}", fontsize=8)
        ax.set_title("Relative Rotation Graph"); ax.set_xlabel("JdK RS-Ratio"); ax.set_ylabel("JdK RS-Momentum"); ax.grid(True, linestyle=':', alpha=0.6)
        fig.tight_layout(); FigureCanvasTkAgg(fig, master=self.rrg_chart_frame).get_tk_widget().pack(fill='both', expand=True)

if __name__ == "__main__":
    app = FinancialDashboardArgs()
    app.mainloop()
