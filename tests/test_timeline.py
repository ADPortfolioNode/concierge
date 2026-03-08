# stub out MemoryStore to avoid external dependencies during unit tests
import memory.memory_store as _ms
_ms.MemoryStore = lambda *args, **kwargs: None

import asyncio

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
    assert 'notice' in resp and 'queued' in resp['notice'].lower()
    # wait for hold to finish
    loop.run_until_complete(task)


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


def test_metrics_endpoint_and_notice(monkeypatch):
    """Metrics endpoint should reflect request counts and produce notice on fallback."""
    from fastapi.testclient import TestClient
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
