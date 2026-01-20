import tokenize
import io
import re

def strip_comments_thorough(file_path, output_comments_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    comments = []
    clean_lines = []
    
    # Use tokenize to accurately find comments
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    
    # Track the last line we processed to handle full lines and inline stuff
    # But tokenize is better for "removing" them.
    # However, user wants them in a txt file.
    
    result = []
    last_row = 1
    last_col = 0
    
    for tok in tokens:
        tok_type, tok_string, (start_row, start_col), (end_row, end_col), line = tok
        
        if tok_type == tokenize.COMMENT:
            comments.append(tok_string + '\n')
            continue
        
        # We need to rebuild the file without comments
        # tokenize.untokenize is better but it preserves comments if they are there.
        # We will manually rebuild
        
        if start_row > last_row:
            result.append('\n' * (start_row - last_row))
            last_col = 0
        
        result.append(' ' * (start_col - last_col))
        result.append(tok_string)
        
        last_row = end_row
        last_col = end_col

    # Write clean file
    with open(file_path, 'w', encoding='utf-8') as f:
    # Remove excessive blank lines (more than 2 newlines becomes 2)
    final_output = "".join(result)
    final_output = re.sub(r'\n{3,}', '\n\n', final_output)
    f.write(final_output)

    # Write comments file
    with open(output_comments_path, 'w', encoding='utf-8') as f:
        f.writelines(comments)

if __name__ == "__main__":
    import sys
    # For some reason tokenize might behave weirdly if we don't handle encoding
    # But this should be fine for standard python files.
    strip_comments_thorough(r"c:\Users\adm\Repositorios\FactorInvesting\Backtesting\financial_dashboard.py", r"c:\Users\adm\Repositorios\FactorInvesting\Backtesting\extracted_comments.txt")
