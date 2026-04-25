import json
import urllib.request

with urllib.request.urlopen('http://127.0.0.1:8001/openapi.json') as resp:
    data = json.load(resp)
for path in sorted(data.get('paths', {}).keys()):
    if path.startswith('/api/v1/tasks'):
        print(path)
