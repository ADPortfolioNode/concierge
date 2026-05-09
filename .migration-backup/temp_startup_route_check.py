from fastapi.testclient import TestClient
import app
print('routes before startup:')
for r in app.app.routes:
    if r.path.startswith('/api/v1') or r.path in ['/ask', '/_health']:
        print(r.path, getattr(r, 'methods', None), type(r).__name__)
print('--- entering TestClient ---')
with TestClient(app.app) as client:
    print('routes after startup:')
    for r in app.app.routes:
        if r.path.startswith('/api/v1') or r.path in ['/ask', '/_health']:
            print(r.path, getattr(r, 'methods', None), type(r).__name__)
    print('GET /api/v1/tasks ->', client.get('/api/v1/tasks').status_code)
    print('GET /api/v1/tasks/abc/status ->', client.get('/api/v1/tasks/abc/status').status_code)
