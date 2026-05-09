import pathlib
p = pathlib.Path('memory/memory_store.py')
s = p.read_text()
print('len', len(s))
print('count """ ->', s.count('"""'))
print("count ''' ->", s.count("'''"))
for q in ['"""', "'''"]:
    idx = s.find(q)
    while idx != -1:
        start = max(0, idx-40)
        end = min(len(s), idx+40)
        print(q, 'at', idx, 'context:', repr(s[start:end]))
        idx = s.find(q, idx+1)
