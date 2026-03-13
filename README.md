# OpenClaw-style agent scaffold (minimal)

**Version:** `1.0.0`

See [RELEASE.md](RELEASE.md) for full release notes and deployment guide.


Prereqs:

- Python 3.11+
- Set `OPENAI_API_KEY` in your environment to enable real LLM calls (optional);
- `matplotlib` is now required for rendering timeline graphs (see `/api/v1/concierge/timeline/graph`).
  when running inside Docker the compose file will forward this variable from
  the host or `.env` file into the `app` container – you must restart the
  stack after changing it.  A missing key causes the service to fall back to
  rule-based responses and placeholder images.  Image generation uses OpenAI's
  image API (`gpt-image-1` model); earlier repository versions referred to the
  older "DALL-E 3" name which is now deprecated.  
  • If the OpenAI image service fails due to rate limits or billing, and you
    have a `GEMINI_API_KEY` defined, the backend will automatically attempt a
    Gemini image request before falling back to a static placeholder.
  • You can also specify `OPENAI_API_KEYS` as a comma-separated list of
    keys; the integration will rotate through them when a rate limit or 429 is
    received and will fall back to Gemini if configured.
  • A family of variables lets you choose default models without changing
    code:
    `OPENAI_DEFAULT_CHAT_MODEL`, `OPENAI_DEFAULT_EMBED_MODEL`,
    `OPENAI_DEFAULT_MODERATE_MODEL` (optional).
  • The built-in LLMTool automatically retries across multiple OpenAI keys and
    will fall back to the Gemini API if all keys are rate-limited (requires
    `GEMINI_API_KEY`).
  • To prevent the backend from being swamped by many simultaneous requests,
    the SacredTimeline layer throttles incoming user inputs using a semaphore
    (configurable via `max_concurrent_requests` in `config/settings.py`).
    The throttle defaults to **2 concurrent requests** but can be lowered.
    When you submit while the system is busy, you'll receive a clear human
    notice such as:
    "OK – still working on the previous request; yours (\"<your text>\") is
    queued and will run shortly."  The metrics endpoint reports how many
    requests were queued.
    additional keys.  When the primary key receives a 429 rate‑limit error the
    tool will automatically retry with the next key in the list, or fall back to
    rule-based output if all keys are exhausted.
  • If you have a `GEMINI_API_KEY` defined, the system will use OpenAI keys
    first; once those are exhausted it will make a call to Google Gemini
    (model specified by `GEMINI_MODEL`, default `text-bison-001`) before
    resorting to the rule-based stub.  This allows you to leverage both
    providers transparently.

Install:

```bash
python -m pip install -r requirements.txt
```

Run the API server (development):

```bash
uvicorn app.main:app --reload --port 8000  # when running locally without containers
```

## Conversation workflow

The server now implements a simple but clear input workflow that keeps the
agent friendly unless the user asks it to do something concrete:

*✦ Multimedia & suggestions:* sample prompts throughout the UI now include
image, audio and video examples so you can immediately try those features.
When a user greets the bot or asks "what can you do?" the assistant will
proactively mention its ability to generate images, transcribe audio, analyse
uploads, etc., helping the app sell itself to curious newcomers.

*✦ Internet searches:* typing phrases such as "search for X", "look up X" or
"web search for latest LLM benchmarks" triggers a ResearchAgent run.  The
system will immediately reply with a progress message, perform the search in
the background using the built-in `WebSearchTool`, and stream the final
summary once available.  This keeps the conversation flowing while data is
collected from the web.

*✦ Topic hints:* the assistant now watches for key nouns in your messages
(images, audio, video, file, goal, etc.) and automatically includes a brief
reminder of the appropriate capability.  Mentioning "audio" will prompt a
hint about transcription, for example, so users don’t need to discover the
feature themselves.


1. **Greetings & small talk** – very short messages ("hi", "hello", "how are you?", etc.)
   are handled directly and elicit a polite, conversational response. A lightweight
   chat prompt is sent to the LLM so the assistant behaves like a companion rather
   than launching task planning.
2. **Goal detection** – longer or goal‑oriented inputs are passed to the
   `Planner`, which attempts to decompose them into ordered subtasks. If
   meaningful tasks are returned the system will spawn `TaskAgent`s to execute
   and synthesize the results.
3. **Fallback conversation** – if the planner produces no tasks or only a trivial
   echo of the user’s comment, the workflow remains in chat mode and returns a
   friendly reply instead of spinning up agents. This prevents noise when the
   user is just chatting.

The frontend understands the `response` field returned by the API and will
render it as the assistant's message, ensuring greetings and small talk appear
naturally in the chat history.

### Message metadata

All responses include a `meta` object containing the raw result produced by
`SacredTimeline`.  The UI stores this separately from the displayed text so
that conversations remain uncluttered; metadata can be surfaced in tooltips or
collapsible panels when needed (e.g. for debugging or showing goal/task
details).
Metadata now also carries information about the LLM provider that produced the
response (`openai`, `gemini`, or `rule-based`) along with any fallback message.
The frontend automatically displays a small badge under each assistant bubble
and within the metadata panel so you can quickly see whether a reply was
served from the primary OpenAI service or generated by Gemini after a rate
limit or billing issue.
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

# bring up the stack and run Playwright end‑to‑end tests (backend logs in playwright_backend.log)
./start.sh --test

# you can also pass extra arguments to the test command via TEST_ARGS, e.g.
TEST_ARGS="tests/e2e.spec.ts --project=chromium -g Concierge UI" ./start.sh --test
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


## API Endpoints

The backend exposes a simple JSON API used by the React frontend and any
other clients.

### POST `/api/v1/concierge/message`

Send a user message to the conversational engine.  The request body must be
JSON and include **either** a `message` property or an `input` property
(the latter is accepted for historical reasons).  Whitespace-only strings are
rejected with a 400 error.

```json
{
  "message": "What is the weather today?"
}
```

The response is wrapped in a generic envelope:

```json
{
  "status": "success",
  "timestamp": "2026-03-06T04:16:06.421054Z",
  "request_id": "...",
  "data": {
    "id": "...",
    "role": "assistant",
    "content": "<assistant reply>",
    "meta": { "raw": { /* full timeline output */ } }
  },
  "meta": {"confidence":null,"priority":null,"media":null},
  "errors": null
}
```

Clients should display `data.content` to end users; the `meta.raw` field
contains structured details used for debugging or advanced UI widgets.

### GET `/api/v1/concierge/conversation`

Returns an array representing the current conversation.  In this simple demo
service the list is always empty, but production systems would persist
messages across requests.

```json
{"status":"success","timestamp":"...","request_id":"...","data":[],"meta":{...},"errors":null}
```

{
  "message": "What is the weather today?"
}
```

The response is always wrapped in the generic `ApiResponse` envelope with a
`data` field containing an object representing the assistant’s reply.  The
`data` object has at least the following properties:

* `id` – an opaque string (millisecond timestamp by default)
* `role` – `
While the core API is text‑based, the frontend is built to support
multimodal requests when paired with a capable model (for example,
Google’s Gemini family).  Here are some sample user prompts you can feed
through the UI or use in automated tests:

```text
• “Here’s a photo of a circuit board with one component circled; what is it?”
• “Screenshot attached: the console shows a crash stack trace—what does it
  mean and how do I fix it?”

### Live progress banner
Both the **Tasks** and **Goals** pages now display a small progress banner at
the top when any background job is active.  It polls `/api/v1/tasks` every few
seconds and shows a linear progress bar plus a toggleable detail list.  The
banner also surfaces the first job’s label (goal title) and a simple elapsed
time counter so you can track progress at a glance.  This makes it easy to
see that work is running without scrolling down to the job panel.
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
