
import sys
import os
import pandas as pd

# Add Backtesting to path
sys.path.append(os.path.join(os.getcwd(), 'Backtesting'))

try:
    import pages.optimization_tool as optimization_tool
except ImportError:
    # Try absolute path if running from root
    sys.path.append(r'd:\Repositorios\FactorInvesting\Backtesting')
    import pages.optimization_tool as optimization_tool

def test_optimization():
    print("Testing PortfolioOptimizer...")
    # Use small list of tickers for speed
    tickers = ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]
    start_date = "2023-01-01"
    
    opt = optimization_tool.PortfolioOptimizer(tickers, start_date)
    # Mock data fetching to avoid network calls if possible, or just limit tickers
    # For now, let's rely on fetch_data but with few tickers
    
    # We can also mock existing data if we want to be pure, but integration test is fine here
    
    results, max_sharpe, min_vol, optimal = opt.optimize(num_portfolios=100)
    
    print("Optimization finished.")
    print("Max Sharpe keys:", max_sharpe.keys())
    print("Max Sharpe Return:", max_sharpe['Return'])
    print("Min Vol Return:", min_vol['Return'])
    print("Optimal Return:", optimal['Return'])

    return results, max_sharpe, min_vol, optimal

if __name__ == "__main__":
    test_optimization()
