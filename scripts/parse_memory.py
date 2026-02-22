import ast, traceback, pathlib
p = pathlib.Path('memory/memory_store.py')
s = p.read_text()
try:
    ast.parse(s)
    print('AST_OK')
except Exception as e:
    traceback.print_exc()
    print('ERR', type(e), e)
