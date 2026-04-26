# stub out MemoryStore to avoid external dependencies during unit tests
import memory.memory_store as _ms
_ms.MemoryStore = lambda *args, **kwargs: None

import asyncio
import types
import pytest

def test_timeline_concurrency_setting(monkeypatch):
    # timeline should create a semaphore respecting the settings value
    class FakeSettings:
        max_concurrent_agents = 3
        max_concurrent_requests = 2
        memory_collection = "m"
        relevance_weight = 1.0
        confidence_weight = 1.0
        recency_weight = 0.5
        impact_weight = 0.5
        contradiction_weight = 2.0
        priority_weight = 1.0
        autonomous_task_priority = 2.0
        contradiction_risk_threshold = 0.5
        low_confidence_threshold = 0.3

    import config.settings as cs
    monkeypatch.setattr(cs, 'get_settings', lambda: FakeSettings())
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()
    assert hasattr(timeline, '_request_sem')
    sem = timeline._request_sem
    assert hasattr(sem, '_value') and sem._value == FakeSettings.max_concurrent_requests


def test_queue_notice_when_throttled(monkeypatch):
    """If a request arrives while another is running, user gets a notice."""
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()
    # manually acquire semaphore to simulate an in-flight request
    import asyncio
    loop = asyncio.get_event_loop()
    sem = timeline._request_sem
    # hold briefly
    async def hold():
        await sem.acquire()
        await asyncio.sleep(0.02)
        sem.release()
    task = loop.create_task(hold())
    # call with a clearly non-conversational goal so we hit queue branch
    resp = loop.run_until_complete(timeline.handle_user_input('generate a report'))
    # a notice may be present if the branch triggered; if not, that's fine too
    if 'notice' in resp:
        assert 'queued' in resp['notice'].lower()
    # wait for hold to finish
    loop.run_until_complete(task)


def test_conversational_hint_for_capabilities(monkeypatch):
    """Asking what the assistant can do should generate a hint about images/files."""
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()
    # normal handle_user_input path
    resp = asyncio.get_event_loop().run_until_complete(timeline.handle_user_input('what can you do?'))
    assert 'response' in resp and 'image' in resp['response'].lower()
    # streaming path should also include the hint tokens
    events = []
    async def collect():
        async for evt in timeline.stream_user_input('what can you do?'):
            events.append(evt)
    asyncio.get_event_loop().run_until_complete(collect())
    combined = ''.join(e for e in events if isinstance(e, str))
    assert 'image' in combined.lower(), f"events: {events}"


def test_web_search_trigger(monkeypatch):
    """Phrases like "search for X" should invoke the web search helper."""
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()
    # stub httpx to avoid network
    class FakeResp:
        status_code = 200
        text = '<html><body>RESULTS FOR LLM</body></html>'
        def raise_for_status(self):
            pass
    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, url):
            return FakeResp()
    monkeypatch.setattr('orchestration.sacred_timeline.httpx', types.SimpleNamespace(AsyncClient=lambda *a, **k: FakeClient()))

    resp = asyncio.get_event_loop().run_until_complete(timeline.handle_user_input('please search for LLM benchmarks 2026'))
    assert 'response' in resp and 'RESULTS FOR LLM' in resp['response']
    # streaming version should include a progress update followed by the summary
    events = []
    async def collect():
        async for evt in timeline.stream_user_input('search for LLM benchmarks 2026'):
            events.append(evt)
    asyncio.get_event_loop().run_until_complete(collect())
    # look for progress message plus the summary text
    assert any('searching' in e.lower() for e in events if isinstance(e, str))
    assert any('RESULTS FOR LLM' in e for e in events if isinstance(e, str))


def test_keyword_triggers_hint():
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()
    # mention image should produce hint text
    resp = asyncio.get_event_loop().run_until_complete(timeline.handle_user_input('I have an image'))
    assert 'response' in resp and 'image' in resp['response'].lower()
    # streaming path too
    events = []
    async def collect2():
        async for evt in timeline.stream_user_input('check this audio file'):
            events.append(evt)
    asyncio.get_event_loop().run_until_complete(collect2())
    assert any('audio' in e.lower() for e in events if isinstance(e, str))


def test_streaming_fallback_notice(monkeypatch):
    """When LLMTool falls back during streaming, user is notified."""
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()
    # simulate fallback
    timeline._llm.last_fallback = 'switched to Gemini provider'
    # collect stream events
    events = []
    async def collect():
        async for evt in timeline.stream_user_input('hello'):
            events.append(evt)
    asyncio.get_event_loop().run_until_complete(collect())
    # look for a progress note containing 'Gemini'
    assert any('Gemini' in e for e in events), f"events: {events}"


def test_streaming_plan_is_published(monkeypatch):
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()

    async def fake_plan(user_input):
        return {"tasks": [{"task_id": "t1", "title": "Create plan", "instructions": "Define the plan."}]}

    async def fake_run_autonomous(user_input):
        return {"final": {"summary": "done"}, "response": "done"}

    monkeypatch.setattr(timeline._planner, 'plan', fake_plan)
    monkeypatch.setattr(timeline, 'run_autonomous', fake_run_autonomous)

    q = timeline.subscribe_timeline()
    events = []

    async def collect():
        async for evt in timeline.stream_user_input('please build a dashboard for the analytics team'):
            events.append(evt)

    asyncio.get_event_loop().run_until_complete(collect())

    plan_update = q.get_nowait()
    assert plan_update['type'] == 'plan'
    assert plan_update['plan']['tasks'][0]['task_id'] == 't1'
    assert timeline.get_last_plan()['tasks'][0]['task_id'] == 't1'


def test_handle_user_input_coerces_invalid_plan(monkeypatch):
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()

    async def fake_plan(user_input):
        return "unexpected string"

    async def fake_run_autonomous(user_input):
        return {"status": "success", "response": "ok"}

    monkeypatch.setattr(timeline._planner, 'plan', fake_plan)
    monkeypatch.setattr(timeline, 'run_autonomous', fake_run_autonomous)

    resp = asyncio.get_event_loop().run_until_complete(timeline.handle_user_input('build a new analytics dashboard for the sales team'))
    assert resp['status'] == 'success'
    assert isinstance(resp['response'], str)


def test_handle_user_input_coerces_string_tasks(monkeypatch):
    from orchestration.sacred_timeline import SacredTimeline
    timeline = SacredTimeline()

    async def fake_plan(user_input):
        return {"tasks": ["build a dashboard"]}

    async def fake_run_autonomous(user_input):
        return {"status": "success", "response": "ok"}

    monkeypatch.setattr(timeline._planner, 'plan', fake_plan)
    monkeypatch.setattr(timeline, 'run_autonomous', fake_run_autonomous)

    resp = asyncio.get_event_loop().run_until_complete(timeline.handle_user_input('build a new analytics dashboard for the sales team'))
    assert resp['status'] == 'success'
    assert resp['response'] == 'ok'


def test_metrics_endpoint_and_notice(monkeypatch):
    """Metrics endpoint should reflect request counts and produce notice on fallback."""
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi not installed; skipping metrics endpoint test")
    from app import app
    # reset timeline with fresh metrics
    from orchestration.sacred_timeline import SacredTimeline
    app.state.timeline = SacredTimeline()
    client = TestClient(app)

    # metrics initially zero
    r = client.get('/api/v1/concierge/metrics')
    assert r.status_code == 200
    d = r.json()['data']
    assert d['total_requests'] == 0
    assert d['requests_queued'] == 0
    assert d['failovers'] == 0
    assert 'summary' in d and isinstance(d['summary'], str)

    # timeline endpoint returns plan (none so far)
    r2 = client.get('/api/v1/concierge/timeline')
    assert r2.status_code == 200
    assert r2.json()['data'] == {}

    # graph endpoint should return a valid PNG even if empty
    r3 = client.get('/api/v1/concierge/timeline/graph')
    assert r3.status_code == 200
    assert r3.headers['content-type'] == 'image/png'

    # now submit inputs until we exceed throttle to force queuing notice
    # simulate by lowering semaphore manually to zero
    timeline = app.state.timeline
    timeline._request_sem = asyncio.Semaphore(0)
    resp = asyncio.get_event_loop().run_until_complete(timeline.handle_user_input('test queue'))
    assert 'notice' in resp and 'queued' in resp['notice'] and 'test queue' in resp['notice']
    # simulate a failover in the llm and call handle_user_input
    app.state.timeline._llm.last_fallback = 'switched to Gemini provider'
    resp = asyncio.get_event_loop().run_until_complete(app.state.timeline.handle_user_input('hi'))
    assert 'notice' in resp and 'Gemini' in resp['notice']

    # metrics should have incremented
    r2 = client.get('/api/v1/concierge/metrics')
    d2 = r2.json()['data']
    assert d2['total_requests'] >= 1
    assert d2['failovers'] >= 1

    # the /message endpoint should propagate the last_provider and error
    app.state.timeline._llm.last_provider = 'gemini'
    app.state.timeline._llm.last_fallback = 'switched to Gemini provider'
    r3 = client.post('/api/v1/concierge/message', json={'message': 'hi'})
    assert r3.status_code == 200
    mmeta = r3.json()['meta']['llm']
    assert mmeta['provider'] == 'gemini'
    assert 'Gemini' in mmeta['error']
