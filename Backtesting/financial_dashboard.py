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
    cache_key = (tuple(sorted(tickers)), start_date, end_date)
    
    if cache_key not in GLOBAL_DATA_CACHE:
        print(f"Baixando novos dados para: {tickers}")
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

        ttk.Label(input_frame, text="Tickers (espaço ou vírgula):").pack(side='left', padx=5)
        self.val_ticker_entry = ttk.Entry(input_frame, width=30)
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

        input_frame = ttk.LabelFrame(self.tab_bt, text="Configuration", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)

        self.bt_tickers_entry = self._add_labeled_entry(input_frame, "Tickers (comma sep):", 0, 0, 50, "BBAS3, BBSE3, CMIG4, CXSE3, TAEE4, TIMS3", 3)
        self.bt_initial_entry = self._add_labeled_entry(input_frame, "Initial Invest (BRL):", 1, 0, 15, "1000")
        self.bt_monthly_entry = self._add_labeled_entry(input_frame, "Monthly Invest (BRL):", 1, 2, 15, "600")
        self.bt_start_entry   = self._add_labeled_entry(input_frame, "Start Date (YYYY-MM-DD):", 2, 0, 15, "2015-01-01")
        self.bt_rf_alloc_entry = self._add_labeled_entry(input_frame, "Risk Free Alloc (%):", 2, 2, 15, "0")

        self.btn_run_bt = ttk.Button(input_frame, text="Run Backtest", command=self.run_backtest_thread)
        self.btn_run_bt.grid(row=3, column=3, sticky='e', padx=5, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.tab_bt, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', padx=10, pady=2)

        self.bt_results_frame = ttk.LabelFrame(self.tab_bt, text="Performance Outcomes", padding=10)
        self.bt_results_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.bt_notebook = ttk.Notebook(self.bt_results_frame)
        self.bt_notebook.pack(fill='both', expand=True)

        self.bt_tab_summary = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(self.bt_tab_summary, text="Summary & Chart")

        self.bt_tree = ttk.Treeview(self.bt_tab_summary, columns=("Metric", "Value", "Notes"), show='headings', height=8)
        self.bt_tree.heading("Metric", text="Metric")
        self.bt_tree.heading("Value", text="Value")
        self.bt_tree.heading("Notes", text="Notes")
        self.bt_tree.column("Metric", width=120)
        self.bt_tree.column("Value", width=100)
        self.bt_tree.pack(side='left', fill='y', padx=5, pady=5)

        self.bt_chart_frame = ttk.Frame(self.bt_tab_summary)
        self.bt_chart_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        self.fig_bt = Figure(figsize=(5, 4), dpi=100)
        self.ax_bt = self.fig_bt.add_subplot(111)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.canvas_bt = FigureCanvasTkAgg(self.fig_bt, master=self.bt_chart_frame)
        self.canvas_bt.get_tk_widget().pack(fill='both', expand=True)

        self.bt_tab_divs = ttk.Frame(self.bt_notebook)
        self.bt_notebook.add(self.bt_tab_divs, text="Monthly Dividends")
        
        self.div_tree = ttk.Treeview(self.bt_tab_divs, show='headings')
        self.div_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        vsb = ttk.Scrollbar(self.bt_tab_divs, orient="vertical", command=self.div_tree.yview)
        vsb.pack(side='right', fill='y')
        self.div_tree.configure(yscrollcommand=vsb.set)

    def run_valuation(self):
        raw_input = self.val_ticker_entry.get().replace(',', ' ')
        tickers = [self._format_ticker(t) for t in raw_input.split() if t.strip()][:4]
    
        if not tickers:
            messagebox.showwarning("Erro de Entrada", "Por favor, insira pelo menos um ticker.")
            return

        self.val_status_label.config(text=f"Buscando dados para: {', '.join(tickers)}...")
        self.val_tree.delete(*self.val_tree.get_children())
        self.update_idletasks()
        
        self._run_in_thread(self._process_valuation_multi, args=(tickers,))

    def _process_valuation_multi(self, tickers):
        try:
            tickers = sorted(tickers)
            
            groups = {
                "Bazin": [],
                "Graham": [],
                "P/E (15x)": [],
                "PEG Ratio": []
            }

            for ticker in tickers:
                stock = yf.Ticker(ticker)
                data = valuation.get_financial_data(stock)

                if not data:
                    continue

                price = data['current_price']
                t_short = ticker.replace('.SA', '')

                bazin_price, bazin_dy = valuation.calculate_bazin(data)
                if bazin_price:
                    upside = ((bazin_price - price) / price) * 100
                    status = "Cheap" if bazin_price > price else "Expensive"
                    groups["Bazin"].append((f"{t_short}", f"R$ {bazin_price:.2f}", f"{upside:+.2f}%", status, f"Yield: {bazin_dy:.2f}%"))
                else:
                    groups["Bazin"].append((f"{t_short}", "N/A", "-", "-", "No Data"))

                graham_price = valuation.calculate_graham(data)
                if graham_price:
                    upside = ((graham_price - price) / price) * 100
                    status = "Cheap" if graham_price > price else "Expensive"
                    groups["Graham"].append((f"{t_short}", f"R$ {graham_price:.2f}", f"{upside:+.2f}%", status, f"Price: R$ {price:.2f}"))
                else:
                    groups["Graham"].append((f"{t_short}", "N/A", "-", "-", "No Data"))

                pe, eps = data.get('pe_ratio'), data.get('eps')
                if pe and eps:
                    fair_pe = 15 * eps
                    upside_pe = ((fair_pe - price) / price) * 100
                    status_pe = "Cheap" if fair_pe > price else "Expensive"
                    groups["P/E (15x)"].append((f"{t_short}", f"R$ {fair_pe:.2f}", f"{upside_pe:+.2f}%", status_pe, f"P/E: {pe:.2f}"))
                else:
                    groups["P/E (15x)"].append((f"{t_short}", "N/A", "-", "-", "No Data"))

                peg_v = valuation.calculate_peg(data)
                if peg_v:
                    status = "Undervalued" if peg_v < 1 else "Overvalued"
                    groups["PEG Ratio"].append((f"{t_short}", f"{peg_v:.2f}", "-", status, "Ideal < 1.0"))
                else:
                    groups["PEG Ratio"].append((f"{t_short}", "N/A", "-", "-", "No Data"))

            final_rows = []
            for method, rows in groups.items():
                if rows:
                    final_rows.append((f"--- {method.upper()} ---", "", "", "", ""))
                    final_rows.extend(rows)
                    final_rows.append(("", "", "", "", ""))

            self.after(0, lambda: self._update_val_table_multi(final_rows))

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Error", error_msg))

    def _update_val_table_multi(self, rows):
        self.val_tree.delete(*self.val_tree.get_children())
        for row in rows:
            self.val_tree.insert("", "end", values=row)
        self.val_status_label.config(text="Comparação concluída.")
        
    def _process_backtest(self, tickers, start_date, end_date, initial_investment, monthly_investment, rf_allocation):
        try:
            self.is_processing = True
            data = get_cached_data(tickers, start_date, end_date)
            
            if data is None or data.empty:
                raise ValueError("Falha ao obter dados.")

            bt = backtest_tool.PortfolioBacktester(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                initial_investment=initial_investment,
                monthly_investment=monthly_investment,
                rf_allocation=rf_allocation,
                injected_data=data
            )
            
            results = bt.run()
            
            if results is None:
                raise ValueError("O backtest não retornou resultados válidos.")

            self.after(0, lambda: self._update_backtest_ui(results))

        except Exception as e:
            mensagem_erro = str(e)
            self.after(0, lambda: messagebox.showerror("Erro no Backtest", str(e)))
        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_run_bt.config(state='normal'))
    def _update_backtest_ui(self, results):
        self.btn_run_bt.config(state='normal')
        self.is_processing = False

        if 'performance' not in results:
            messagebox.showerror("Erro", "Dados de performance ausentes nos resultados.")
            return

        for i in self.bt_tree.get_children(): 
            self.bt_tree.delete(i)
        
        perf = results['performance']
        stats = results.get('stats', {})
        
        final_with = perf['with_reinvest'].iloc[-1]
        final_no = perf['no_reinvest'].iloc[-1]
        final_ibov = perf['ibov'].iloc[-1]
        final_cdi = perf['cdi'].iloc[-1]
        final_inv = perf['invested_capital'].iloc[-1]

        retorno_total = ((final_with / final_inv) - 1) * 100 if final_inv > 0 else 0

        metrics = [
            ("Retorno Total", f"{retorno_total:.2f}%", "No período inteiro"),
            ("CAGR", f"{stats.get('cagr', 0):.2f}%", "Retorno Anual Composto"),
            ("Volatilidade", f"{stats.get('volatility', 0):.2f}%", "Risco Anualizado"),
            ("Max Drawdown", f"{stats.get('max_drawdown', 0):.2f}%", "Maior Queda Histórica"),
            ("Beta vs IBOV", f"{stats.get('beta', 0):.2f}", "Sensibilidade ao Mercado"),
            ("---", "---", "---"),
            ("Final: Com Reinvest.", f"R$ {final_with:,.2f}", "Estratégia Principal"),
            ("Final: Sem Reinvest.", f"R$ {final_no:,.2f}", "Dividendos no Caixa"),
            ("Final: IBOVESPA", f"R$ {final_ibov:,.2f}", "Somente Índice"),
            ("Final: CDI", f"R$ {final_cdi:,.2f}", "Renda Fixa Risk Free"),
            ("Total Investido", f"R$ {final_inv:,.2f}", "Soma dos Aportes")
        ]
        
        for m in metrics:
            self.bt_tree.insert("", "end", values=m)

        self.ax_bt.clear()
        
        self.ax_bt.plot(perf.index, perf['with_reinvest'], label="Com Reinvestimento", color='#00ff00', linewidth=2)
        self.ax_bt.plot(perf.index, perf['no_reinvest'], label="Sem Reinvestimento", color='#00bbff', linewidth=1.5)
        self.ax_bt.plot(perf.index, perf['ibov'], label="Somente IBOV", color='#ffffff', alpha=0.5)
        self.ax_bt.plot(perf.index, perf['cdi'], label="Somente CDI", color='#ffcc00', linestyle='--')
        self.ax_bt.plot(perf.index, perf['invested_capital'], label="Total Investido", color='#888888', linestyle=':')
        
        self.ax_bt.set_title("Evolução Patrimonial: Comparativo de Estratégias")
        self.ax_bt.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f'R${x:,.0f}'))
        self.ax_bt.legend(fontsize='small', loc='upper left')
        self.ax_bt.grid(True, alpha=0.2)
        self.canvas_bt.draw()

        for i in self.div_tree.get_children(): 
            self.div_tree.delete(i)
            
        div_matrix = results.get('div_matrix')
        
        if div_matrix is not None and not div_matrix.empty:
            cols = ["Ano", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez", "Total"]
            self.div_tree["columns"] = cols
            
            for c in cols:
                self.div_tree.heading(c, text=c)
                self.div_tree.column(c, width=65, anchor='center')

            for year, row in div_matrix.iterrows():
                row_data = [str(int(year))]
                y_total = 0
                for m in range(1, 13):
                    val = row.get(m, 0.0)
                    if pd.isna(val): val = 0.0
                    
                    row_data.append(f"R$ {val:,.2f}" if val > 0 else "-")
                    y_total += val
                    
                row_data.append(f"R$ {y_total:,.2f}")
                self.div_tree.insert("", "end", values=row_data)
            
    def run_backtest_thread(self):
        if self.is_processing:
            messagebox.showwarning("Aviso", "Aguarde o término do processo atual.")
            return

        tickers_raw = self.bt_tickers_entry.get().replace(',', ' ')
        tickers = []
        for t in tickers_raw.split():
            t = t.strip().upper()
            if t and not any(ext in t for ext in ['.SA', '.X', '^']):
                tickers.append(f"{t}.SA")
            elif t:
                tickers.append(t)
        
        start_date = self.bt_start_entry.get()
        end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            initial_investment = float(self.bt_initial_entry.get())
            monthly_investment = float(self.bt_monthly_entry.get())
            rf_allocation = float(self.bt_rf_alloc_entry.get()) / 100.0
        except ValueError:
            messagebox.showerror("Erro", "Valores de investimento e alocação devem ser números.")
            return

        self.btn_run_bt.config(state='disabled')
        self.is_processing = True
        self.progress_var.set(10)
        
        self._run_in_thread(self._process_backtest, args=(tickers, start_date, end_date, initial_investment, monthly_investment, rf_allocation))

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

        self.opt_frontier_tab = ttk.Frame(self.opt_chart_notebook)
        self.opt_perf_tab = ttk.Frame(self.opt_chart_notebook)
        self.opt_chart_notebook.add(self.opt_frontier_tab, text="Efficient Frontier")
        self.opt_chart_notebook.add(self.opt_perf_tab, text="Historical Performance")

        self.fig_opt = Figure(figsize=(6, 4), dpi=100)
        self.ax_opt = self.fig_opt.add_subplot(111)
        self.canvas_opt = FigureCanvasTkAgg(self.fig_opt, master=self.opt_frontier_tab)
        self.canvas_opt.get_tk_widget().pack(fill='both', expand=True)

        self.fig_opt_hist = Figure(figsize=(6, 4), dpi=100)
        self.ax_opt_hist = self.fig_opt_hist.add_subplot(111)
        self.canvas_opt_hist = FigureCanvasTkAgg(self.fig_opt_hist, master=self.opt_perf_tab)
        self.canvas_opt_hist.get_tk_widget().pack(fill='both', expand=True)

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
        if self.is_processing:
            messagebox.showwarning("Aviso", "Aguarde o término do processo atual.")
            return

        tickers_raw = self.opt_tickers_entry.get().replace(',', ' ')
        tickers = []
        for t in tickers_raw.split():
            t = t.strip().upper()
            if t and not any(ext in t for ext in ['.SA', '.X', '^']):
                tickers.append(f"{t}.SA")
            elif t:
                tickers.append(t)

        start_date = self.opt_start_entry.get()
        end_date = datetime.now().strftime('%Y-%m-%d')

        if not tickers or not start_date:
            messagebox.showwarning("Aviso", "Preencha Tickers e Data de Início.")
            return

        self.btn_run_opt.config(state='disabled')
        self.is_processing = True
        
        self._run_in_thread(self._process_optimization, args=(tickers, start_date, end_date))

    def _process_optimization(self, tickers, start_date, end_date):
        try:
            self.is_processing = True
            data = get_cached_data(tickers, start_date, end_date)
            
            if data is None or data.empty:
                raise ValueError("Falha ao obter dados para otimização.")

            opt = optimization_tool.PortfolioOptimizer(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                price_data=data
            )
            
            results = opt.optimize()
            self.after(0, lambda: self._update_optimization_ui(results))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro na Otimização", str(e)))
        finally:
            self.is_processing = False
            self.after(0, lambda: self.btn_run_opt.config(state='normal'))

    def _update_optimization_ui(self, results):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        
        self.btn_run_opt.config(state='normal')
        self.is_processing = False

        if not results or len(results) != 4:
            messagebox.showerror("Erro", "Resultados da otimização não estão no formato esperado.")
            return

        p_results, max_sharpe, min_vol, optimal = results

        results_frame = None
        for child in self.tab_opt.winfo_children():
            if isinstance(child, ttk.LabelFrame) and "Configuration" not in child.cget("text"):
                results_frame = child
                break
                
        if not results_frame:
            results_frame = self.tab_opt.winfo_children()[-1]

        if not hasattr(self, '_opt_layout_built'):
            for widget in results_frame.winfo_children():
                widget.destroy()

            self.opt_tree = ttk.Treeview(results_frame, show='headings')
            self.opt_tree.pack(side='left', fill='y', padx=5, pady=5)

            self.opt_notebook = ttk.Notebook(results_frame)
            self.opt_notebook.pack(side='right', fill='both', expand=True, padx=5, pady=5)

            self.tab_front = ttk.Frame(self.opt_notebook)
            self.opt_notebook.add(self.tab_front, text="Fronteira Eficiente")
            self.fig_front = Figure(figsize=(5, 4), dpi=100)
            self.fig_front.patch.set_facecolor('#121212')
            self.ax_front = self.fig_front.add_subplot(111)
            self.canvas_front = FigureCanvasTkAgg(self.fig_front, master=self.tab_front)
            self.canvas_front.get_tk_widget().pack(fill='both', expand=True)

            self.tab_hist = ttk.Frame(self.opt_notebook)
            self.opt_notebook.add(self.tab_hist, text="Crescimento Histórico")
            self.fig_hist = Figure(figsize=(5, 4), dpi=100)
            self.fig_hist.patch.set_facecolor('#121212')
            self.ax_hist = self.fig_hist.add_subplot(111)
            self.canvas_hist = FigureCanvasTkAgg(self.fig_hist, master=self.tab_hist)
            self.canvas_hist.get_tk_widget().pack(fill='both', expand=True)

            self._opt_layout_built = True

        for i in self.opt_tree.get_children(): 
            self.opt_tree.delete(i)

        self.opt_tree["columns"] = ("Ativo_Metrica", "Max_Sharpe", "Min_Vol", "Optimal")
        self.opt_tree.heading("Ativo_Metrica", text="Ativo / Métrica")
        self.opt_tree.heading("Max_Sharpe", text="Max Sharpe")
        self.opt_tree.heading("Min_Vol", text="Min Vol")
        self.opt_tree.heading("Optimal", text="Optimal")
        self.opt_tree.column("Ativo_Metrica", width=120, anchor='w')
        self.opt_tree.column("Max_Sharpe", width=90, anchor='center')
        self.opt_tree.column("Min_Vol", width=90, anchor='center')
        self.opt_tree.column("Optimal", width=90, anchor='center')

        tickers = list(max_sharpe['Weights'].keys())
        self.opt_tree.insert("", "end", values=("--- PESOS DOS ATIVOS ---", "---", "---", "---"))
        for t in tickers:
            w_ms = max_sharpe['Weights'].get(t, 0) * 100
            w_mv = min_vol['Weights'].get(t, 0) * 100
            w_op = optimal['Weights'].get(t, 0) * 100
            self.opt_tree.insert("", "end", values=(t, f"{w_ms:.1f}%", f"{w_mv:.1f}%", f"{w_op:.1f}%"))

        self.opt_tree.insert("", "end", values=("", "", "", ""))
        self.opt_tree.insert("", "end", values=("--- PERFORMANCE ---", "---", "---", "---"))
        self.opt_tree.insert("", "end", values=("Retorno Esperado", f"{max_sharpe['Return']*100:.2f}%", f"{min_vol['Return']*100:.2f}%", f"{optimal['Return']*100:.2f}%"))
        self.opt_tree.insert("", "end", values=("Volatilidade", f"{max_sharpe['Volatility']*100:.2f}%", f"{min_vol['Volatility']*100:.2f}%", f"{optimal['Volatility']*100:.2f}%"))
        self.opt_tree.insert("", "end", values=("Sharpe Ratio", f"{max_sharpe['Sharpe']:.2f}", f"{min_vol['Sharpe']:.2f}", f"{optimal['Sharpe']:.2f}"))
        self.opt_tree.insert("", "end", values=("Max Drawdown", f"{max_sharpe.get('MaxDrawdown', 0)*100:.2f}%", f"{min_vol.get('MaxDrawdown', 0)*100:.2f}%", f"{optimal.get('MaxDrawdown', 0)*100:.2f}%"))

        self.ax_front.clear()
        self.ax_front.set_facecolor('#121212')
        self.ax_front.scatter(p_results[1], p_results[0], c=p_results[2], cmap='viridis', marker='o', s=10, alpha=0.4)
        self.ax_front.scatter(max_sharpe['Volatility'], max_sharpe['Return'], color='red', marker='*', s=150, label='Max Sharpe', edgecolors='white')
        self.ax_front.scatter(min_vol['Volatility'], min_vol['Return'], color='blue', marker='*', s=150, label='Min Volatility', edgecolors='white')
        self.ax_front.scatter(optimal['Volatility'], optimal['Return'], color='white', marker='*', s=150, label='Optimal', edgecolors='white')
        self.ax_front.set_title("Fronteira Eficiente")
        self.ax_front.set_xlabel("Risco (Volatilidade)")
        self.ax_front.set_ylabel("Retorno Esperado")
        self.ax_front.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        self.ax_front.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        self.ax_front.legend(fontsize='small')
        self.canvas_front.draw()

        self.ax_hist.clear()
        self.ax_hist.set_facecolor('#121212')
        curve_ms = max_sharpe.get('EquityCurve')
        curve_mv = min_vol.get('EquityCurve')
        curve_op = optimal.get('EquityCurve')
        
        if curve_ms is not None and not curve_ms.empty:
            self.ax_hist.plot(curve_ms.index, curve_ms.values, label="Max Sharpe", color='red', linewidth=1.5)
            self.ax_hist.plot(curve_mv.index, curve_mv.values, label="Min Volatilidade", color='blue', linewidth=1.5)
            self.ax_hist.plot(curve_op.index, curve_op.values, label="Optimal", color='white', linewidth=2.5)
            self.ax_hist.set_title("Crescimento Histórico (Base 100)")
            self.ax_hist.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, p: f'{x:,.0f}'))
            self.ax_hist.legend(fontsize='small')
            self.ax_hist.grid(True, alpha=0.2)
        else:
            self.ax_hist.set_title("Histórico Indisponível")
            
        self.canvas_hist.draw()
        
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
