# OpenClaw-style agent scaffold (minimal)

**Version:** `1.0.0`

See [RELEASE.md](RELEASE.md) for full release notes and deployment guide.


Prereqs:

- Python 3.11+
- Set `OPENAI_API_KEY` in your environment to enable real LLM calls (optional)

Install:

```bash
python -m pip install -r requirements.txt
```

Run the API server (development):

```bash
uvicorn app.main:app --reload --port 8000  # when running locally without containers
```

> **Note:** in the Docker Compose setup the FastAPI app is exposed on host port
> **8001** to avoid conflicting with the Chroma vector database, which listens on
> 8000. The helper script maps `8001:8000` for the `app` service.

You can also run the React frontend locally from the `frontend/` directory:

```bash
cd frontend
npm install        # first time only (the helper script does this on startup too)
npm run dev         # starts Vite on http://localhost:5173
```

> **Note:** earlier versions of this repository erroneously specified
> `zustand@^4.6.0` in `frontend/package.json`; that release does not exist on
> npm.  If `npm install` fails with a "No matching version" error, check the
> dependency section and bump to a valid `5.x` release (current latest is
> `5.0.11`).

New: the frontend can be run inside a container using Docker Compose. A
`frontend` service has been added to `docker-compose.yml`:

```yaml
  frontend:
    image: node:18-alpine
    container_name: quesarc_frontend
    working_dir: /app
    ports:
      - "5173:5173"
    # project files are bind‑mounted for live editing.
    # node_modules lives in a separate named volume so that Linux native
    # packages are installed inside the container; this avoids the
    # "MODULE_NOT_FOUND" errors that occurred when Windows-built modules were
    # mounted into the Alpine container.
    volumes:
      - ./frontend:/app:cached
      - frontend_node_modules:/app/node_modules
    command: ["sh","-c","npm ci && npm run dev"]
```

Because the container now populates its own `node_modules` at startup, the
host-side `npm install` step is optional and exists primarily for editors or
local builds. `start.sh` will still run `npm install` on the host for
convenience, but the container's `npm ci` ensures correct dependencies for
its platform regardless of what lives on the host.

Logs from the frontend container are appended to `start.log` when `--log` is
used, and you can always view them via `docker-compose logs frontend`.

After the container is running you should be able to open the UI at
`http://localhost:5173` in a browser; the Vite dev server proxy is configured
for hot reload and will reflect changes to the `frontend/` source.

> **Note:** in the Docker Compose setup the FastAPI app is exposed on host port
> **8001** to avoid conflicting with the Chroma vector database, which listens on
> 8000. The helper script maps `8001:8000` for the `app` service.

A helper script `start.sh` is also provided for managing the local
Docker Compose environment. It wraps common workflows such as pruning
stale containers, building images, and emitting diagnostics. By default the
script will start the backend services **and** the frontend container; use
`--no-frontend` if you only need the API.

```bash
# default: bring the full stack (including frontend) up
./start.sh

# clean everything, rebuild and log diagnostics
./start.sh --prune --yes --build --diag

# explicitly clear/rebuild the stack (down then up --build)
./start.sh --clear

# skip the frontend service
./start.sh --no-frontend
```

The script accepts flags `--prune`, `--yes`, `--build`, `--diag`, and
`--clear` to control behavior.

Over time `start.sh` has been hardened; it now:

- checks for the Docker CLI/daemon and a working compose implementation
- chooses between `docker-compose` and `docker compose` automatically
- traps errors and reports the failing line number
- prints helpful diagnostics when things go wrong
- handles platform quirks (PowerShell `npm.cmd`, execution policies, etc.)
- optionally validates and logs the frontend container status after launch

These improvements make the helper robust enough for daily development and
CI usage.

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

## Phase 8 – Scalable Concurrent Reasoning

The system now supports running multiple root goals concurrently using a
shared `AsyncConcurrencyManager` with priority queuing. The intelligence
store evolved into a directed graph (`IntelligenceGraph`) capturing lineage,
confidence scores, and contradiction risks. Agents can perform reflection and
reuse previous context when confidence is low. Tasks spawn adaptively during
execution, and self-initiated refinement occurs when contradictions or
low-confidence nodes are detected. The test suite includes `tests/phase8_tests.py`
which validates concurrency metrics, graph integrity, reflection bounds, and
retrieval performance.

## Phase 9 – Adaptive Self‑Optimizing Intelligence

Building on Phase 8, the platform now computes deterministic priority scores
for tasks and memory artifacts. The score considers relevance, prior
confidence, impact, contradiction risk, and explicit priority flags. A
priority queue ensures high‑importance work is scheduled first. The memory
retrieval engine biases results by confidence, contradiction risk, and encoded
priorities. Nodes evolve confidence over time, contradictions are flagged
automatically, and a pruning mechanism archives stale low‑confidence data.

The coordinator can spawn autonomous reconciliation or refinement tasks when
issues are detected, and a dedicated testing script `tests/phase9_tests.py`
exercises priority ordering, contradiction detection, graph pruning, and
retrieval bias.

### Running the Tests

```bash
python tests/phase8_tests.py  # concurrency & graph integrity
python tests/phase9_tests.py  # adaptive priority and self‑refinement
```

## Phase 10 – Fully Autonomous Cross‑Task Orchestration

The system now handles multiple tasks, resolves conflicts, and persists
cross-run intelligence deterministically. CriticAgent enforces strict
validation without auto-approval; graph nodes update rather than duplicate.
Memory recall is enriched with task metadata and autonomous refinement
limits prevent runaway loops. New tests (`tests/phase10_tests.py`) and
harness checks ensure cross-task reuse, critic strictness, and graph
state updates.


## Example prompts for UI testing

While the core API is text‑based, the frontend is built to support
multimodal requests when paired with a capable model (for example,
Google’s Gemini family).  Here are some sample user prompts you can feed
through the UI or use in automated tests:

```text
• “Here’s a photo of a circuit board with one component circled; what is it?”
• “Screenshot attached: the console shows a crash stack trace—what does it
  mean and how do I fix it?”
• “Listen to this short audio clip (French); please transcribe and translate
  it.”
• “Watch this 10‑second video of someone entering a room; describe what
  happens.”
• “The following diagram shows our architecture (image); list any security
  weaknesses you spot.”
``` 

These examples exercise the “multimedia prompt” path: the frontend sends the
text together with the binary asset to the backend, which forwards it to the
LLM.  Your integration tests can stub the response in the same way the
existing Playwright tests stub the `/api/v1/concierge/message` endpoint.

## Phase 11 – Distributed Multi‑Node Orchestration

Nodes can now run concurrently across a cluster while sharing a centralized
intelligence graph. A global concurrency manager enforces both per-node and
system-wide limits. MemoryStore synchronizes updates and supports delta
writes; task scheduling uses a simple round‑robin distributor. The frontend
remains unchanged since API contracts are consistent across nodes.

A new testing harness (`tests/phase11_tests.py`) simulates multiple nodes and
validates distributed task execution, cross-node memory consistency, and
global concurrency enforcement. The capability harness includes a
`distributed_execution` scenario to exercise this behaviour.

### Running the Distributed Tests

```bash
python tests/phase11_tests.py  # distributed and consistency checks
```
Building on Phase 8, the platform now computes deterministic priority scores
for tasks and memory artifacts. The score considers relevance, prior
confidence, impact, contradiction risk, and explicit priority flags. A
priority queue ensures high‑importance work is scheduled first. The memory
retrieval engine biases results by confidence, contradiction risk, and encoded
priorities. Nodes evolve confidence over time, contradictions are flagged
automatically, and a pruning mechanism archives stale low‑confidence data.

The coordinator can spawn autonomous reconciliation or refinement tasks when
issues are detected, and a dedicated testing script `tests/phase9_tests.py`
exercises priority ordering, contradiction detection, graph pruning, and
retrieval bias.

### Running the Tests

```bash
python tests/phase8_tests.py  # concurrency & graph integrity
python tests/phase9_tests.py  # adaptive priority and self‑refinement
```

---

## Changelog

- **v0.6.0-phase6-stable**: Added persistent vector DB (Qdrant/Chroma) with restart-safe fallback, specialized Research/Coding/Critic agents, in-place refinement, deterministic routing, strict concurrency, depth/refine caps, deduplication, and phase‑6 harness.
- **v0.7.0-phase7a**: Added SynthesizerAgent for final aggregation, multi-root task orchestration support, and expanded harness checks to validate final synthesis. Persistence now stores structured synthesis results.

POST /agent with JSON `{"prompt":"..."}` to run the agent.

## Changelog

- **v0.6.0-phase6-stable**: Added persistent vector DB (Qdrant/Chroma) with restart-safe fallback, specialized Research/Coding/Critic agents, in-place refinement, deterministic routing, strict concurrency, depth/refine caps, deduplication, and phase‑6 harness.
- **v0.7.0-phase7a**: Added SynthesizerAgent for final aggregation, multi-root task orchestration support, and expanded harness checks to validate final synthesis. Persistence now stores structured synthesis results.

POST /agent with JSON `{"prompt":"..."}` to run the agent.
