"""Unit tests for the plugin and integration capability layers (Phase 13)."""

from __future__ import annotations

import asyncio
import pytest
import types

# ---------------------------------------------------------------------------
# Plugin layer tests
# ---------------------------------------------------------------------------

from plugins.base_plugin import BasePlugin
from plugins.plugin_registry import PluginRegistry
from plugins.summarization_plugin import SummarizationPlugin
from plugins.image_generation_plugin import ImageGenerationPlugin


class _EchoPlugin(BasePlugin):
    name = "echo"
    description = "Returns input unchanged."

    async def run(self, input_data):
        return input_data


# --- Registry ---------------------------------------------------------------

def test_plugin_registry_register_and_get():
    reg = PluginRegistry()
    p = _EchoPlugin()
    reg.register(p)
    assert reg.get("echo") is p


def test_plugin_registry_list_plugins():
    reg = PluginRegistry()
    reg.register(_EchoPlugin())
    items = reg.list_plugins()
    assert len(items) == 1
    assert items[0]["name"] == "echo"
    assert items[0]["type"] == "plugin"


def test_plugin_registry_enabled_only():
    class _DisabledPlugin(_EchoPlugin):
        name = "disabled_echo"
        enabled = False

    reg = PluginRegistry()
    reg.register(_EchoPlugin())
    reg.register(_DisabledPlugin())
    assert len(reg.list_plugins(enabled_only=False)) == 2
    assert len(reg.list_plugins(enabled_only=True)) == 1


def test_plugin_registry_replace():
    reg = PluginRegistry()
    reg.register(_EchoPlugin())
    reg.register(_EchoPlugin())  # second registration should replace
    assert len(reg.list_plugins()) == 1


def test_plugin_registry_unregister():
    reg = PluginRegistry()
    reg.register(_EchoPlugin())
    reg.unregister("echo")
    assert reg.get("echo") is None


def test_plugin_registry_empty_name_raises():
    class _Unnamed(BasePlugin):
        name = ""
        async def run(self, _):
            return None

    reg = PluginRegistry()
    with pytest.raises(ValueError):
        reg.register(_Unnamed())


# --- Built-in plugins -------------------------------------------------------

def test_summarization_plugin_short_text():
    plugin = SummarizationPlugin()
    result = asyncio.get_event_loop().run_until_complete(plugin.run("Hello world"))
    assert result == "Hello world"


def test_summarization_plugin_truncates():
    plugin = SummarizationPlugin()
    long_text = "x" * 300
    result = asyncio.get_event_loop().run_until_complete(plugin.run(long_text))
    # Implementation: text[:197] + "…" — the ellipsis is 1 char, total = 198
    assert len(result) == 198
    assert result.endswith("…")


def test_summarization_plugin_empty():
    plugin = SummarizationPlugin()
    result = asyncio.get_event_loop().run_until_complete(plugin.run(""))
    assert result == ""


def test_image_generation_plugin_returns_dict():
    plugin = ImageGenerationPlugin()
    result = asyncio.get_event_loop().run_until_complete(plugin.run("a red fox on a hill"))
    assert isinstance(result, dict)
    assert "url" in result
    assert "prompt" in result


def test_plugin_to_dict():
    plugin = SummarizationPlugin()
    d = plugin.to_dict()
    assert d["name"] == "summarization"
    assert d["type"] == "plugin"
    assert "version" in d


# ---------------------------------------------------------------------------
# Integration layer tests
# ---------------------------------------------------------------------------

from integrations.base_integration import BaseIntegration
from integrations.integration_registry import IntegrationRegistry
from integrations.openai_integration import OpenAIIntegration
from integrations.gemini_integration import GeminiIntegration
from integrations.stripe_integration import StripeIntegration
from integrations.slack_integration import SlackIntegration


class _MockIntegration(BaseIntegration):
    name = "mock"
    description = "Test stub."
    service = "MockService"

    async def call(self, action, payload=None):
        return {"action": action, "payload": payload}


def test_integration_registry_register_and_get():
    reg = IntegrationRegistry()
    intg = _MockIntegration()
    reg.register(intg)
    assert reg.get("mock") is intg


def test_integration_registry_list():
    reg = IntegrationRegistry()
    reg.register(_MockIntegration())
    items = reg.list_integrations()
    assert len(items) == 1
    assert items[0]["name"] == "mock"
    assert items[0]["type"] == "integration"


def test_integration_registry_unregister():
    reg = IntegrationRegistry()
    reg.register(_MockIntegration())
    reg.unregister("mock")
    assert reg.get("mock") is None


def test_integration_empty_name_raises():
    class _Unnamed(BaseIntegration):
        name = ""
        service = "x"
        async def call(self, action, payload=None):
            return None

    reg = IntegrationRegistry()
    with pytest.raises(ValueError):
        reg.register(_Unnamed())


def test_stub_integrations_call():
    # wipe environment to force integrations into unconfigured/stubbed state
    import os
    for var in ("OPENAI_API_KEY", "OPENAI_API_KEYS", "GEMINI_API_KEY",
                "STRIPE_SECRET_KEY", "SLACK_BOT_TOKEN", "SLACK_WEBHOOK_URL"):
        os.environ.pop(var, None)

    for cls in (OpenAIIntegration, GeminiIntegration, StripeIntegration, SlackIntegration):
        intg = cls()
        result = asyncio.get_event_loop().run_until_complete(intg.call("test"))
        assert result["integration"] == intg.name
        # status should indicate unconfigured or stubbed; at minimum it must be a
        # string and not cause an exception.
        assert isinstance(result.get("status"), str)


def test_openai_integration_rate_limit_fallback(monkeypatch):
    # create a fake openai module so we can control behavior
    import sys, types
    class DummyError(Exception):
        pass

    class DummyClient:
        def __init__(self, api_key):
            self.api_key = api_key
            # build nested attributes matching SDK
            class Chat:
                class Completions:
                    async def create(inner_self, model, messages):
                        if api_key == "primary":
                            # simulate rate limit on first key
                            raise DummyError("rate limit")
                        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="fallback-ok"))], model="m", usage={})
                completions = Completions()
            self.chat = Chat()
            class Embeddings:
                async def create(inner_self, model, input):
                    return types.SimpleNamespace(data=[], model=model)
            self.embeddings = Embeddings()
            class Moderations:
                async def create(inner_self, input):
                    return types.SimpleNamespace(results=[types.SimpleNamespace(flagged=False, categories={})])
            self.moderations = Moderations()

    fake = types.ModuleType("openai")
    fake.AsyncOpenAI = DummyClient
    fake.error = types.SimpleNamespace(RateLimitError=DummyError)
    sys.modules["openai"] = fake

    # avoid slowing tests by patching asyncio.sleep with an async stub
    async def _noop_sleep(s):
        pass
    monkeypatch.setattr("asyncio.sleep", _noop_sleep)

    monkeypatch.setenv("OPENAI_API_KEY", "primary")
    monkeypatch.setenv("OPENAI_API_KEYS", "fallback")

    intg = OpenAIIntegration()
    resp = asyncio.get_event_loop().run_until_complete(
        intg.call("chat", {"messages": [{"role": "user", "content": "hi"}]})
    )
    assert resp["status"] == "ok"
    assert resp["content"] == "fallback-ok"


def test_openai_integration_gemini_fallback(monkeypatch):
    # prepare fake openai import that always raises 429 for each key
    import sys, types
    class DummyError(Exception):
        pass
    class DummyClient:
        def __init__(self, api_key):
            pass
        class Chat:
            class Completions:
                async def create(inner_self, model, messages):
                    raise DummyError("rate limit")
            completions = Completions()
        chat = Chat()
        class Embeddings:
            async def create(inner_self, model, input):
                raise DummyError("rate limit")
        embeddings = Embeddings()
        class Moderations:
            async def create(inner_self, input):
                raise DummyError("rate limit")
        moderations = Moderations()
    fake = types.ModuleType("openai")
    fake.AsyncOpenAI = DummyClient
    fake.error = types.SimpleNamespace(RateLimitError=DummyError)
    sys.modules["openai"] = fake

    # patch the gemini_chat helper on the integration for predictable output
    async def fake_gemini(self, prompt_or_payload, model, action):
        return {"integration": self.name, "action": action, "status": "ok", "content": "gemout", "model": model}
    monkeypatch.setenv("OPENAI_API_KEY", "primary")
    monkeypatch.setenv("OPENAI_API_KEYS", "secondary")
    monkeypatch.setenv("GEMINI_API_KEY", "gemkey")
    monkeypatch.setattr(OpenAIIntegration, "_gemini_chat", fake_gemini)
    # patch sleep again so backoff doesn't delay
    async def _noop_sleep(s):
        pass
    monkeypatch.setattr("asyncio.sleep", _noop_sleep)

    intg = OpenAIIntegration()
    resp = asyncio.get_event_loop().run_until_complete(
        intg.call("chat", {"messages": [{"role": "user", "content": "hey"}]})
    )
    assert resp["status"] == "ok"
    assert resp["content"] == "gemout"



def test_gemini_integration_rate_limit_retry(monkeypatch):
    """Gemini client should retry once when the first call returns 429."""
    # ensure integration thinks it's configured
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    import types
    import httpx

    call_count = {"n": 0}
    class DummyClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        async def post(self, url, json, headers):
            call_count["n"] += 1
            class Resp:
                def raise_for_status(inner):
                    if call_count["n"] == 1:
                        # first attempt simulate 429
                        raise httpx.HTTPStatusError("429", request=None, response=types.SimpleNamespace(status_code=429))
                    return None
                def json(inner):
                    return {"candidates": [{"output": "ok"}]}
            return Resp()

    monkeypatch.setattr("httpx.AsyncClient", lambda timeout=None: DummyClient())

    intg = GeminiIntegration()
    resp = asyncio.get_event_loop().run_until_complete(
        intg.call("chat", {"messages": [{"role": "user", "content": "hi"}]})
    )
    assert resp["status"] == "ok"
    assert resp["content"] == "ok"
    assert call_count["n"] == 2


def test_integration_health_check_without_key():
    """Integrations report health correctly based on configured keys."""
    import os
    # clear relevant variables for deterministic behavior
    for var in ("OPENAI_API_KEY", "OPENAI_API_KEYS", "GEMINI_API_KEY"):
        os.environ.pop(var, None)

    # OpenAIIntegration should now be unhealthy when no keys, then healthy with gemini
    intg = OpenAIIntegration()
    res1 = asyncio.get_event_loop().run_until_complete(intg.health_check())
    assert res1 is False
    os.environ["GEMINI_API_KEY"] = "gemkey"
    intg2 = OpenAIIntegration()
    res2 = asyncio.get_event_loop().run_until_complete(intg2.health_check())
    assert res2 is True

    # other integrations simply return bool and may be uncontrolled
    for cls in (StripeIntegration, SlackIntegration):
        intg = cls()
        result = asyncio.get_event_loop().run_until_complete(intg.health_check())
        assert isinstance(result, bool)


def test_openai_integration_environment_model_override(monkeypatch):
    # ensure OPENAI_DEFAULT_CHAT_MODEL affects the request
    import sys, types
    class DummyClient:
        def __init__(self, api_key):
            self.api_key = api_key
            class Chat:
                class Completions:
                    async def create(inner_self, model, messages):
                        # echo model back so we can inspect it
                        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=model))], model=model, usage={})
                completions = Completions()
            self.chat = Chat()
            class Embeddings:
                async def create(inner_self, model, input):
                    return types.SimpleNamespace(data=[], model=model)
            self.embeddings = Embeddings()
            class Moderations:
                async def create(inner_self, input):
                    return types.SimpleNamespace(results=[types.SimpleNamespace(flagged=False, categories={})])
            self.moderations = Moderations()

    fake = types.ModuleType("openai")
    fake.AsyncOpenAI = DummyClient
    fake.error = types.SimpleNamespace(RateLimitError=Exception)
    sys.modules["openai"] = fake

    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_DEFAULT_CHAT_MODEL", "my-special-model")

    intg = OpenAIIntegration()
    resp = asyncio.get_event_loop().run_until_complete(
        intg.call("chat", {"messages": [{"role": "user", "content": "hi"}]})
    )
    assert resp["status"] == "ok"
    assert resp["content"] == "my-special-model"

    # embedding model should also respect environment
    monkeypatch.setenv("OPENAI_DEFAULT_EMBED_MODEL", "embed-me")
    resp2 = asyncio.get_event_loop().run_until_complete(
        intg.call("embed", {"input": "foo"})
    )
    assert resp2["status"] == "ok"
    assert resp2["model"] == "embed-me"


def test_integration_to_dict():
    intg = _MockIntegration()
    d = intg.to_dict()
    assert d["name"] == "mock"
    assert d["service"] == "MockService"
    assert d["type"] == "integration"


# ---------------------------------------------------------------------------
# Plugin loader test
# ---------------------------------------------------------------------------

def test_load_default_plugins():
    from plugins.plugin_loader import load_default_plugins
    from plugins.plugin_registry import PluginRegistry, _REG

    # Load into a fresh registry to avoid side effects
    fresh_reg = PluginRegistry()
    original_reg = None

    import plugins.plugin_registry as pr
    original_reg = pr._REG
    pr._REG = fresh_reg
    try:
        load_default_plugins()
        names = {p["name"] for p in fresh_reg.list_plugins()}
        assert "summarization" in names
        assert "image_generation" in names
    finally:
        pr._REG = original_reg


def test_load_default_integrations():
    from integrations.integration_loader import load_default_integrations
    import integrations.integration_registry as ir

    fresh_reg = IntegrationRegistry()
    original_reg = ir._REG
    ir._REG = fresh_reg
    try:
        load_default_integrations()
        names = {i["name"] for i in fresh_reg.list_integrations()}
        assert "openai" in names
        assert "stripe" in names
        assert "slack" in names
    finally:
        ir._REG = original_reg


def test_llmtool_fallback_to_gemini(monkeypatch):
    """LLMTool should call Gemini if all OpenAI keys rate-limit or are unauthorized."""
    import httpx, types

    # simulate a client that always throws 429 on stream()
    class DummyClient:
        def __init__(self, timeout=None):
            pass
        def stream(self, method, url, json, headers, timeout):
            class CM:
                async def __aenter__(self_inner):
                    raise httpx.HTTPStatusError("429", request=None, response=types.SimpleNamespace(status_code=429))
                async def __aexit__(self_inner, exc_type, exc, tb):
                    return False
            return CM()

    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_API_KEYS", "other")
    monkeypatch.setenv("GEMINI_API_KEY", "gemkey")
    monkeypatch.setattr("tools.llm_tool._get_client", lambda: DummyClient())
    # override gemini call to return a known string
    async def fake_call(self, p, c):
        return "gemresponse"
    from tools.llm_tool import LLMTool
    monkeypatch.setattr(LLMTool, "_call_gemini", fake_call)
    async def _noop_sleep(s):
        pass
    monkeypatch.setattr("asyncio.sleep", _noop_sleep)

    from tools.llm_tool import LLMTool
    tool = LLMTool()
    resp = asyncio.get_event_loop().run_until_complete(tool.generate("hello"))
    assert resp == "gemresponse"


def test_openai_integration_unauthorized_fallback(monkeypatch):
    # fake openai client raising 401 then fallback to gemini
    import sys, types
    class DummyError(Exception):
        pass
    class DummyClient:
        def __init__(self, api_key):
            pass
        class Chat:
            class Completions:
                async def create(inner_self, model, messages):
                    error = DummyError("unauthorized")
                    error.response = types.SimpleNamespace(status_code=401)
                    raise error
            completions = Completions()
        chat = Chat()
        class Embeddings:
            async def create(inner_self, model, input):
                error = DummyError("unauthorized")
                error.response = types.SimpleNamespace(status_code=401)
                raise error
        embeddings = Embeddings()
        class Moderations:
            async def create(inner_self, input):
                error = DummyError("unauthorized")
                error.response = types.SimpleNamespace(status_code=401)
                raise error
        moderations = Moderations()
    fake = types.ModuleType("openai")
    fake.AsyncOpenAI = DummyClient
    fake.error = types.SimpleNamespace(RateLimitError=DummyError)
    sys.modules["openai"] = fake

    async def fake_gemini(self, prompt_or_payload, model, action):
        return {"integration": self.name, "action": action, "status": "ok", "content": "gemout", "model": model}
    monkeypatch.setenv("OPENAI_API_KEY", "primary")
    monkeypatch.setenv("OPENAI_API_KEYS", "secondary")
    monkeypatch.setenv("GEMINI_API_KEY", "gemkey")
    monkeypatch.setattr(OpenAIIntegration, "_gemini_chat", fake_gemini)
    async def _noop_sleep(s):
        pass
    monkeypatch.setattr("asyncio.sleep", _noop_sleep)

    intg = OpenAIIntegration()
    resp = asyncio.get_event_loop().run_until_complete(
        intg.call("chat", {"messages": [{"role": "user", "content": "hey"}]})
    )
    assert resp["status"] == "ok"
    assert resp["content"] == "gemout"
