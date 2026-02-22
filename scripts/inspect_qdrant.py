from qdrant_client import QdrantClient
import os
host = os.getenv('QDRANT_HOST','localhost')
port = int(os.getenv('QDRANT_PORT','6333'))
try:
    client = QdrantClient(url=f'http://{host}:{port}')
    cols = client.get_collections()
    print('collections:', cols)
    try:
        info = client.get_collection(collection_name='sacred_memory')
        print('sacred_memory info:', info)
    except Exception as e:
        print('get_collection failed:', e)
except Exception as e:
    print('client init failed:', e)
