import os, sys, time
from pathlib import Path

# ensure project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault('VECTOR_DB', 'qdrant')
from memory.memory_store import MemoryStore

ms = MemoryStore(collection_name='debug_collection')
time.sleep(0.5)
print('client_initialized:', ms._client is not None)
print('vector_db:', ms._vector_db)
print('is_qdrant:', ms._is_qdrant)
print('client_type:', type(ms._client))
