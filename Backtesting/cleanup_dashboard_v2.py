import os

file_path = r"c:\Users\adm\Repositorios\FactorInvesting\Backtesting\financial_dashboard.py"

if not os.path.exists(file_path):
    print(f"Error: {file_path} not found.")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
blank_count = 0

for line in lines:
    stripped = line.strip()
    if not stripped:
        blank_count += 1
    else:
        # We found a code line.
        # Process the preceding blanks.
        if new_lines: # Don't add blank lines at the very start of the file
            # Logic: K blanks -> max(0, K-1) blanks, capped at 2.
            # Determine how many newlines to insert.
            num_blanks_to_insert = min(2, max(0, blank_count - 1))
            for _ in range(num_blanks_to_insert):
                new_lines.append("")
        
        # Add the code line (rstrip to remove trailing newline/spaces, we'll add newline later)
        new_lines.append(line.rstrip())
        blank_count = 0

# Handle trailing blanks? (Usually we don't want them)
# If we wanted to keep one newline at EOF, we can ensure the last written item has a newline.

with open(file_path, 'w', encoding='utf-8') as f:
    for i, line in enumerate(new_lines):
        f.write(line)
        if i < len(new_lines) - 1:
            f.write("\n")
    f.write("\n") # Ensure single newline at EOF

print(f"Cleanup complete. Processed {len(lines)} lines into {len(new_lines)} lines.")
