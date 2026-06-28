import requests
r = requests.get('http://localhost:8001/openapi.json', timeout=20)
print('status', r.status_code)
paths = r.json().get('paths', {})
print('task list path present:', '/api/v1/tasks' in paths)
print('task id path present:', '/api/v1/tasks/{task_id}' in paths)
print('task status path present:', '/api/v1/tasks/{task_id}/status' in paths)
print('health path present:', '/_health' in paths)
print('ask path present:', '/ask' in paths)
print('paths count', len(paths))
print('paths sample:')
for p in sorted(paths)[:50]:
    if p.startswith('/api/v1/') or p in ['/ask', '/_health']:
        print(p)
