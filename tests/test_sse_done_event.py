import json
import os
import time

import pytest
import requests


def test_sse_done_event_is_structured_dict():
    base = os.getenv("BASE_URL", "http://localhost:8001").rstrip('/')
    url = os.getenv("CONCIERGE_SSE_URL", f"{base}/api/v1/concierge/stream")
    payload = {"message": f"pytest sse probe {time.time()}"}
    with requests.post(url, json=payload, stream=True, headers={"Accept": "text/event-stream"}, timeout=120) as r:
        assert r.status_code == 200, f"Unexpected status: {r.status_code}"
        start = time.time()
        for raw in r.iter_lines(decode_unicode=True):
            # skip empty lines
            if not raw:
                continue
            line = raw.strip()
            # SSE lines are often prefixed with 'data:'
            if line.startswith("data:"):
                data = line[len("data:"):].strip()
                try:
                    obj = json.loads(data)
                except Exception:
                    # ignore non-JSON data
                    continue
                # look for the final done event
                if isinstance(obj, dict) and obj.get("type") == "done":
                    result = obj.get("result")
                    assert isinstance(result, dict), f"done.result is not a dict: {type(result)}"
                    return
            # safety timeout for the test
            if time.time() - start > 90:
                break
    pytest.fail("Did not receive a 'done' event with a structured dict result")
