import urllib.request, urllib.error
import os
base = os.getenv('BASE_URL', 'http://localhost:8001').rstrip('/')
u = os.getenv('METRICS_URL', f"{base}/metrics")
try:
    req = urllib.request.Request(u, method='GET')
    with urllib.request.urlopen(req, timeout=10) as r:
        print('URL:', u, 'STATUS', r.status)
        ct = r.getheader('Content-Type')
        print('Content-Type:', ct)
        data = r.read(1000)
        print('Body (first 1000 bytes):')
        print(data.decode('utf-8', errors='replace')[:1000])
except urllib.error.HTTPError as e:
    print('URL:', u, 'HTTP ERROR', e.code)
    try:
        print('BODY:', e.read().decode('utf-8', errors='replace')[:800])
    except Exception as ex:
        print('BODY READ ERROR', ex)
except Exception as ex:
    print('URL:', u, 'ERROR', ex)
