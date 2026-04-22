import importlib
try:
    t = importlib.import_module('tasks')
    print('tasks module', t)
    print('task_router attr', hasattr(t, 'task_router'))
    print('task_router type', type(getattr(t, 'task_router', None)))
    tr = getattr(t, 'task_router', None)
    if tr is not None:
        print('router prefix', tr.prefix)
        for r in tr.routes:
            print('route', r.path, getattr(r, 'methods', None), type(r).__name__)
except Exception as e:
    import traceback; traceback.print_exc()
