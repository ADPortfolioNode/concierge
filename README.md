# OpenClaw-style agent scaffold (minimal)

Prereqs:

- Python 3.11+
- Set `OPENAI_API_KEY` in your environment to enable real LLM calls (optional)

Install:

```bash
python -m pip install -r requirements.txt
```

Run the API server (development):

```bash
uvicorn app.main:app --reload --port 8000
```

POST /agent with JSON `{"prompt":"..."}` to run the agent.
