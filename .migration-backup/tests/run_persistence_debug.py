import os,sys,asyncio,traceback,importlib
ROOT = r'E:\\2024 RESET\\concierge'
sys.path.insert(0, ROOT)
os.environ.setdefault('VECTOR_DB','qdrant')
try:
    mod = importlib.import_module('tests.persistence_test')
    print('module imported, running main...')
    asyncio.run(mod.main())
    print('main completed')
except Exception:
    traceback.print_exc()
