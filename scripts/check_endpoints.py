import os
import sys
import urllib.error
import urllib.request

# allow overriding base URL via CLI arg (positional or --base-url=<url> / --base-url <url>)
# or env BASE_URL.
base = None
args = sys.argv[1:]
i = 0
while i < len(args):
    arg = args[i]
    if arg.startswith('--base-url='):
        base = arg.split('=', 1)[1]
    elif arg == '--base-url' and i + 1 < len(args):
        base = args[i + 1]
        i += 1
    elif not arg.startswith('--'):
        # positional argument — backward-compatible usage
        base = arg
    i += 1

if not base:
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
