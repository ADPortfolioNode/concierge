import asyncio
import time
import json

import os

# allow overriding when probing non-local servers (CI, staging, etc.)
base = os.getenv('BASE_URL', 'http://localhost:8001').rstrip('/')
url = f"{base}/api/v1/concierge/stream"
payload = {"message": f"sse probe from agent {time.time()}"}

async def run_httpx():
    try:
        import httpx
    except Exception as e:
        raise RuntimeError("httpx not available") from e
    async with httpx.AsyncClient(timeout=None) as client:
        print(f"POST {url} -> sending payload: {payload}")
        r = await client.post(url, json=payload, headers={"Accept": "text/event-stream"}, timeout=None)
        print("Status:", r.status_code)
        print("Headers:", dict(r.headers))
        start = time.time()
        try:
            async for line in r.aiter_lines():
                now = time.time()
                elapsed = now - start
                print(f"{elapsed:0.3f}s | {line}")
                if line and ('[DONE]' in line or '"type": "done"' in line):
                    print("Received done marker; stopping read loop.")
                    return
                if elapsed > 60:
                    print("Reached 60s window; stopping.")
                    return
        except Exception as exc:
            print("Exception while reading lines:", exc)


def run_requests():
    try:
        import requests
    except Exception as e:
        raise RuntimeError("requests not available") from e
    print(f"POST {url} -> sending payload: {payload}")
    with requests.post(url, json=payload, stream=True, headers={"Accept": "text/event-stream"}, timeout=None) as r:
        print("Status:", r.status_code)
        print("Headers:", dict(r.headers))
        start = time.time()
        try:
            for raw in r.iter_lines(decode_unicode=True):
                now = time.time()
                elapsed = now - start
                print(f"{elapsed:0.3f}s | {raw}")
                if raw and ('[DONE]' in raw or '"type": "done"' in raw):
                    print("Received done marker; stopping read loop.")
                    return
                if elapsed > 60:
                    print("Reached 60s window; stopping.")
                    return
        except Exception as exc:
            print("Exception while reading lines:", exc)


async def main():
    # prefer requests (sync) in this environment, fall back to httpx async
    try:
        run_requests()
    except Exception as e:
        print("requests path failed or not available:", e)
        print("Falling back to httpx async")
        try:
            await run_httpx()
        except Exception as e2:
            print("httpx path failed or not available:", e2)


if __name__ == '__main__':
    asyncio.run(main())
