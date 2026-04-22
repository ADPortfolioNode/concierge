import requests

urls = [
    'http://localhost:8001/api/v1/tasks',
    'http://localhost:8001/api/v1/tasks/doesnotexist',
    'http://localhost:8001/openapi.json',
]
for url in urls:
    try:
        r = requests.get(url, timeout=10)
        print(url, r.status_code)
        print('CORS:', r.headers.get('access-control-allow-origin'))
        print(r.text[:400].replace('\n', '\\n'))
    except Exception as e:
        print(url, 'ERROR', e)
