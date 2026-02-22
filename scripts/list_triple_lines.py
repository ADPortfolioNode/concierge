from pathlib import Path
p = Path('memory/memory_store.py')
lines = p.read_text().splitlines()
for i,l in enumerate(lines, start=1):
    if '"""' in l or "'''" in l:
        print(i, l)
