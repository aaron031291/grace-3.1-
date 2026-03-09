import re
with open('consensus_output.txt', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
    # Remove terminal escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_text = ansi_escape.sub('', text)
    # Remove carriage returns that overwrite lines
    clean_text = clean_text.replace('\r', '')
with open('consensus_clean.txt', 'w', encoding='utf-8') as f:
    f.write(clean_text)
