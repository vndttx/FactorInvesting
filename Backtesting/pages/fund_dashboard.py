import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
from datetime import datetime
import sys
import os

# Ensure we can import from the same directory or package
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from Backtesting import fund_tool
except ImportError:
    # If running directly from Backtesting folder
    import pages.fund_tool as fund_tool

class FundDashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fund Analysis Tool")
        self.geometry("1000x800")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.create_fund_ui()
        
    def create_fund_ui(self):
        # Input Section
        input_frame = ttk.LabelFrame(self.main_frame, text="Fund Selection", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)
        
        # Row 1: CNPJ
        ttk.Label(input_frame, text="CNPJ (e.g. 13.823.084/0001-05):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.fund_cnpj_entry = ttk.Entry(input_frame, width=25)
        self.fund_cnpj_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.fund_cnpj_entry.insert(0, "13.823.084/0001-05")  # Fund with confirmed data
        
        # Row 2: Date range
        self.fund_use_full_period = tk.BooleanVar(value=True)
        chk_full_period = ttk.Checkbutton(input_frame, text="Use full period", 
                                          variable=self.fund_use_full_period,
                                          command=self._toggle_fund_dates)
        chk_full_period.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Start:").grid(row=1, column=1, sticky='e', padx=5, pady=5)
        self.fund_start_entry = ttk.Entry(input_frame, width=12)
        self.fund_start_entry.grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.fund_start_entry.insert(0, "2025-01-01")
        
        ttk.Label(input_frame, text="End:").grid(row=1, column=3, sticky='e', padx=5, pady=5)
        self.fund_end_entry = ttk.Entry(input_frame, width=12)
        self.fund_end_entry.grid(row=1, column=4, sticky='w', padx=5, pady=5)
        self.fund_end_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # Initial state: disable date entries
        self._toggle_fund_dates()
        
        # Row 3: Analyze button
        self.btn_fund_analyze = ttk.Button(input_frame, text="Analyze Fund", command=self.run_fund_analysis_thread)
        self.btn_fund_analyze.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Results Area
        self.fund_results_frame = ttk.LabelFrame(self.main_frame, text="Analysis Results", padding=10)
        self.fund_results_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.fund_info_label = ttk.Label(self.fund_results_frame, text="Enter a CNPJ and click Analyze", font=('Arial', 10))
        self.fund_info_label.pack(pady=5)
        
        # Chart Area
        self.fund_chart_frame = ttk.Frame(self.fund_results_frame)
        self.fund_chart_frame.pack(fill='both', expand=True)

    def _toggle_fund_dates(self):
        """Enable/disable date entry fields based on full period checkbox"""
        if self.fund_use_full_period.get():
            self.fund_start_entry.config(state='disabled')
            self.fund_end_entry.config(state='disabled')
        else:
            self.fund_start_entry.config(state='normal')
            self.fund_end_entry.config(state='normal')

    def run_fund_analysis_thread(self):
        cnpj = self.fund_cnpj_entry.get().strip()
        if not cnpj:
            messagebox.showwarning("Input Error", "Please enter a CNPJ.")
            return

        self.btn_fund_analyze.config(state='disabled')
        self.fund_info_label.config(text="Fetching data from CVM (this might take a minute)...")
        
        # Clear previous chart
        for widget in self.fund_chart_frame.winfo_children(): widget.destroy()
        
        # Get date values in main thread (Tkinter requirement)
        use_full_period = self.fund_use_full_period.get()
        start_date_str = self.fund_start_entry.get() if not use_full_period else None
        end_date_str = self.fund_end_entry.get() if not use_full_period else None
        
        t = threading.Thread(target=self._process_fund_analysis, 
                           args=(cnpj, use_full_period, start_date_str, end_date_str))
        t.start()

    def _process_fund_analysis(self, cnpj, use_full_period, start_date_str, end_date_str):
        try:
            ff = fund_tool.FundFetcher()
            bf = fund_tool.BenchmarkFetcher()
            
            # 1. Get Metadata
            meta = ff.get_fund_metadata(cnpj)
            
            # Robustness: If metadata missing, define defaults but don't stop
            if not meta:
                print(f"Metadata not found for {cnpj}, trying to fetch history anyway...")
                # Default to a reasonable start date (e.g. 2010) if we can't find real one
                default_start = datetime(2010, 1, 1)
                meta = {
                    'name': f"Fund {cnpj} (Metadata Missing)",
                    'start_date': default_start,
                    'status': 'Unknown',
                    'class': 'Unknown'
                }
            
            start_date = meta['start_date']
            
            # 2. Get Fund History
            if use_full_period:
                print(f"Fetching full period starting from {start_date.year}")
                fund_hist = ff.get_fund_history(cnpj, start_year=start_date.year)
            else:
                try:
                    # Parse user-provided dates first
                    user_start = pd.to_datetime(start_date_str)
                    user_end = pd.to_datetime(end_date_str)
                    
                    print(f"User requested range: {user_start} to {user_end}")
                    
                    # Optimization: Only fetch from the requested start year
                    # (Unless requested start is before inception, then use inception)
                    req_year = user_start.year
                    fetch_year = max(req_year, start_date.year)
                    
                    print(f"Fetching history starting from {fetch_year}")
                    fund_hist = ff.get_fund_history(cnpj, start_year=fetch_year)
                    
                    # Filter to exact date range
                    if not fund_hist.empty:
                        # Ensure index is datetime
                        if not isinstance(fund_hist.index, pd.DatetimeIndex):
                            fund_hist.index = pd.to_datetime(fund_hist.index)
                            
                        # Handle potential timezone mismatch by making naive
                        if fund_hist.index.tz is not None:
                            fund_hist.index = fund_hist.index.tz_localize(None)
                            
                        fund_hist = fund_hist[(fund_hist.index >= user_start) & (fund_hist.index <= user_end)]
                        print(f"Filtered to {len(fund_hist)} records")
                        
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    messagebox.showwarning("Date Error", f"Invalid date format used. Reverting to full period.\nError: {e}")
                    fund_hist = ff.get_fund_history(cnpj, start_year=start_date.year)
            
            if fund_hist.empty:
                raise ValueError("No historical quota data found for this fund.")
            
            # 3. Get Benchmarks (aligned to Fund Start)
            real_start = fund_hist.index[0]
            
            # Fetch benchmarks with error handling - make them optional
            cdi = bf.get_cdi(real_start)
            ipca = bf.get_ipca(real_start)
            ibov = bf.get_ibov(real_start)
            
            # 4. Merge and Normalize
            df = pd.DataFrame({'Fund': fund_hist['VL_QUOTA']})
            
            # Helper to safely join
            def safe_join(main_df, other, col_name):
                if other.empty:
                    return main_df
                
                # Ensure it's a Series with the right name
                if isinstance(other, pd.DataFrame):
                    other = other.iloc[:, 0]
                
                other.name = col_name
                return main_df.join(other, how='left')

            # Only add benchmarks that have data
            if not cdi.empty:
                df = safe_join(df, cdi, "CDI")
            
            if not ipca.empty:
                # IPCA special handling (reindex)
                if isinstance(ipca, pd.DataFrame):
                    ipca = ipca.iloc[:, 0]
                ipca_daily = ipca.reindex(df.index, method='ffill')
                df['IPCA'] = ipca_daily
            
            if not ibov.empty:
                if isinstance(ibov, pd.DataFrame):
                    ibov = ibov.iloc[:, 0]
                    
                if ibov.index.tz is not None:
                    ibov.index = ibov.index.tz_convert(None)
                df = safe_join(df, ibov, "Ibovespa")
            
            # Fill any NaN values
            df = df.ffill()
            
            # Drop rows with any remaining NaN (usually first row only)
            df = df.dropna()
            
            if df.empty or len(df) == 0:
                # Fallback: if merging killed all data, show fund only
                df = pd.DataFrame({'Fund': fund_hist['VL_QUOTA']})
                if df.empty:
                     raise ValueError("No data available.")
            
            # Normalize to 100
            first_values = df.iloc[0]
            normalized = (df / first_values) * 100
            
            self.after(0, lambda: self._show_fund_results(normalized, meta))
            
        except Exception as e:
            # Simple error message is enough now that we removed the rename bug
            error_msg = str(e)
            print(f"Error in process_fund_analysis: {error_msg}")
            
            # Print full trace to console for debug
            import traceback
            traceback.print_exc()
            
            self.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.after(0, lambda: self.fund_info_label.config(text=f"Error: {error_msg}"))
        finally:
             self.after(0, lambda: self.btn_fund_analyze.config(state='normal'))

    def _show_fund_results(self, df, meta):
        # Update Info Label
        info_text = f"Fund: {meta['name']}\nStart Date: {meta['start_date'].strftime('%Y-%m-%d')}\n"
        
        # Calculate Returns
        total_return = (df.iloc[-1] / 100 - 1) * 100
        info_text += "\nTotal Return:\n"
        for col in df.columns:
            info_text += f"{col}: {total_return[col]:.2f}%  "
            
        self.fund_info_label.config(text=info_text)
        
        # Plot
        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        
        for col in df.columns:
            # Highlight Fund line
            linewidth = 2.5 if col == 'Fund' else 1.5
            alpha = 1.0 if col == 'Fund' else 0.7
            ax.plot(df.index, df[col], label=col, linewidth=linewidth, alpha=alpha)
            
        ax.set_title("Performance Comparison (Base 100)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Normalized Return")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.6)
        
        canvas = FigureCanvasTkAgg(fig, master=self.fund_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

if __name__ == "__main__":
    app = FundDashboardApp()
    app.mainloop()
