import app
routes = [(r.path, getattr(r, 'methods', None), type(r).__name__) for r in app.app.routes]
for path, methods, kind in sorted(routes):
    print(path, methods, kind)
print('TOTAL', len(routes))
