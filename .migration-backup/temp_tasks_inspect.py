import importlib
tasks=importlib.import_module('tasks')
print('task_router', hasattr(tasks,'task_router'))
tr=getattr(tasks,'task_router', None)
print('routes', [r.path for r in tr.routes] if tr else None)
