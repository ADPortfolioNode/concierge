import app
print('imported app')
for r in app.app.routes:
    if r.path.startswith('/api/v1') or r.path == '/ask' or r.path == '/_health':
        print(r.path, getattr(r, 'methods', None), type(r).__name__)
print('total', len(app.app.routes))
