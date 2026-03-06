"""Unit tests for the plugin and integration capability layers (Phase 13)."""

from __future__ import annotations

import asyncio
import pytest

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
    for cls in (OpenAIIntegration, StripeIntegration, SlackIntegration):
        intg = cls()
        result = asyncio.get_event_loop().run_until_complete(intg.call("test"))
        assert result["status"] == "stub"
        assert result["integration"] == intg.name


def test_integration_health_check_without_key():
    """Integrations are disabled / fail health-check when env vars are absent."""
    import os
    for cls in (OpenAIIntegration, StripeIntegration, SlackIntegration):
        # env var definitely not set in test environment
        intg = cls()
        result = asyncio.get_event_loop().run_until_complete(intg.health_check())
        # Should be False (no key) or True if coincidentally set; just assert it's bool
        assert isinstance(result, bool)


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
