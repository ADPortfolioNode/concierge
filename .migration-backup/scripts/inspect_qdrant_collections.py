import json
import sys

try:
    from qdrant_client import QdrantClient
    client = QdrantClient(url='http://localhost:6333')
    try:
        cols = client.get_collections()
        print(json.dumps({'method':'qdrant_client','collections': cols}, default=str, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, indent=2))
except Exception:
    # fallback to HTTP
    try:
        from urllib.request import urlopen
        with urlopen('http://localhost:6333/collections') as r:
            data = r.read().decode('utf-8')
            print(json.dumps({'method':'http','collections': json.loads(data)}, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
