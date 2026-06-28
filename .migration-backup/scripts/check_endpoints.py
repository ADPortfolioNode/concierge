import urllib.request, urllib.error, os, sys

# allow overriding base URL via CLI arg or env BASE_URL
base = None
if len(sys.argv) > 1:
    base = sys.argv[1]
else:
    base = os.getenv('BASE_URL', 'http://localhost:8001')

urls=[f'{base}/api/v1/concierge/timeline/graph', f'{base}/api/v1/concierge/media']

for u in urls:
    try:
        req=urllib.request.Request(u, method='GET')
        with urllib.request.urlopen(req, timeout=10) as r:
            print('URL:',u,'STATUS',r.status)
            ct=r.getheader('Content-Type')
            print('Content-Type:',ct)
            data=r.read(200)
            print('First bytes:', data[:64])
    except urllib.error.HTTPError as e:
        print('URL:',u,'HTTP ERROR',e.code)
        try:
            print('BODY:',e.read().decode('utf-8',errors='replace')[:800])
        except Exception as ex:
            print('BODY READ ERROR',ex)
    except Exception as ex:
        print('URL:',u,'ERROR',ex)
