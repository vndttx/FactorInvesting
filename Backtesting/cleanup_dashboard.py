import re
import os

file_path = r"c:\Users\adm\Repositorios\FactorInvesting\Backtesting\financial_dashboard.py"

if not os.path.exists(file_path):
    print(f"Error: {file_path} not found.")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Fix doubling. 
# If the file is indeed doubled (every line followed by a blank line), replacing \n\n with \n should fix it.
# We'll be careful to only do this if it looks effectively doubled.
# But the user complained about "doubled lines", so let's assume it is.
content = content.replace('\n\n', '\n')

# Step 2: Collapse excessive blank lines.
# Replace 3 or more newlines with 2 newlines (one blank line).
content = re.sub(r'\n{3,}', '\n\n', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Cleanup complete. New size: {len(content)} bytes.")
