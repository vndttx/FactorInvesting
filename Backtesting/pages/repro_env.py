import sys
import os

print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not Set')}")
print(f"sys.path: {sys.path}")

def check_import(name):
    try:
        module = __import__(name)
        print(f"[SUCCESS] {name} is installed. Version: {getattr(module, '__version__', 'Unknown')}")
        return True
    except ImportError as e:
        print(f"[ERROR] {name} is NOT installed. Error: {e}")
        return False

check_import("yfinance")
check_import("pandas")
check_import("numpy")
check_import("matplotlib")

try:
    import tkinter
    print(f"[SUCCESS] tkinter is available. Version: {tkinter.TkVersion}")
except ImportError:
    print("[ERROR] tkinter is NOT available.")

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    print("[SUCCESS] matplotlib.backends.backend_tkagg is available.")
except Exception as e:
    print(f"[ERROR] matplotlib.backends.backend_tkagg check failed: {e}")
