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

A helper script `start.sh` is also provided for managing the local
Docker Compose environment. It wraps common workflows such as pruning
stale containers, building images, and emitting diagnostics. Usage:

```bash
# default: tear down any previous stack and bring services up
./start.sh

# clean everything, rebuild and log diagnostics
./start.sh --prune --yes --build --diag

# explicitly clear/rebuild the stack (down then up --build)
./start.sh --clear
```

The script accepts flags `--prune`, `--yes`, `--build`, `--diag`, and
`--clear` to control behavior.

## Build & Docker

The repository includes a `Dockerfile` and `docker-compose.yml` to
spin up supporting services (e.g. a vector database). You can use
`start.sh` or manually invoke `docker-compose`:

```bash
# start containers (with prior down to avoid port conflicts)
docker-compose down || true
docker-compose up -d
```

`start.sh` simplifies this with additional options such as
`--clear` and `--build` as shown above.

## Memory & Recall

Phase 7B introduces deterministic memory recall across independent root
tasks. Before planning a goal, the coordinator queries the persistent memory
store for relevant prior intelligence using keyword matching. When any
relevant artifacts are found, they are injected into every task's context and
agents are encouraged to reason over them. The ResearchAgent will explicitly
prepend a `context:` marker when using prior summaries, and the CriticAgent
verifies that recall tasks reference the memory and produces delta reasoning.

Observability logs track memory retrieval counts, used artifact IDs, and
whether reflections were reused:

```
[MEMORY] retrieval_count=#
[MEMORY] artifacts_used=[ids]
[MEMORY] reflection_reused=True/False
```

Capability tests include a dedicated `memory_recall_test` which now passes
deterministically, confirming the feature.

## Changelog

- **v0.6.0-phase6-stable**: Added persistent vector DB (Qdrant/Chroma) with restart-safe fallback, specialized Research/Coding/Critic agents, in-place refinement, deterministic routing, strict concurrency, depth/refine caps, deduplication, and phase‑6 harness.
- **v0.7.0-phase7a**: Added SynthesizerAgent for final aggregation, multi-root task orchestration support, and expanded harness checks to validate final synthesis. Persistence now stores structured synthesis results.

POST /agent with JSON `{"prompt":"..."}` to run the agent.
