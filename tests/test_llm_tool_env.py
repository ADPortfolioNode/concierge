import os
import importlib


def test_conversational_reply_uses_openai_hint_when_key_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    # reload module to ensure env is read if needed
    llm_tool = importlib.reload(importlib.import_module("tools.llm_tool"))

    reply = llm_tool._conversational_reply("What can you do?")
    assert "To unlock full AI responses" not in reply
    assert "I can use your configured OpenAI key" in reply


def test_conversational_reply_suggests_key_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEYS", raising=False)
    try:
        import dotenv
        monkeypatch.setattr(dotenv, 'load_dotenv', lambda *args, **kwargs: None)
    except ImportError:
        pass
    llm_tool = importlib.reload(importlib.import_module("tools.llm_tool"))

    reply = llm_tool._conversational_reply("What can you do?")
    assert "To unlock full AI responses" in reply
