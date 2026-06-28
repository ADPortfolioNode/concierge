import importlib, traceback
try:
    importlib.invalidate_caches()
    import memory.memory_store as ms
    print('IMPORT_OK')
except Exception:
    traceback.print_exc()
