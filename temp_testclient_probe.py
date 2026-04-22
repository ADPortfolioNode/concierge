from fastapi.testclient import TestClient
import app
client = TestClient(app.app)
print('routes after startup:')
for r in app.app.routes:
    if r.path.startswith('/api/v1') or r.path in ['/ask', '/_health']:
        print(r.path, getattr(r, 'methods', None), type(r).__name__)
print('total', len(app.app.routes))
resp = client.get('/api/v1/tasks')
print('/api/v1/tasks', resp.status_code, resp.text)
resp2 = client.get('/api/v1/tasks/doesnotexist')
print('/api/v1/tasks/doesnotexist', resp2.status_code, resp2.text)
resp3 = client.get('/api/v1/tasks/abc/status')
print('/api/v1/tasks/abc/status', resp3.status_code, resp3.text)
