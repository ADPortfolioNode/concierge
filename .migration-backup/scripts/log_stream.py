import time
import urllib.request

URL = 'http://127.0.0.1:8000/health/logs?limit=200'
OUT = 'backend_logs_stream.txt'

def fetch_once():
    try:
        with urllib.request.urlopen(URL, timeout=5) as r:
            data = r.read().decode('utf-8', errors='replace')
        return data
    except Exception as e:
        return f'<error: {e!r}>'

def main():
    while True:
        ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        v = fetch_once()
        with open(OUT, 'a', encoding='utf-8') as f:
            f.write('==== ' + ts + ' ====\n')
            f.write(v + '\n')
        time.sleep(2)

if __name__ == '__main__':
    main()
