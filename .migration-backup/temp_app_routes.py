from app import app
paths = [route.path for route in app.router.routes if route.path.startswith('/api/v1/tasks')]
print(paths)
