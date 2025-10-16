# PORTFOLIO PROJECT

[https://github.com/B-emiral/Portfolio](https://github.com/B-emiral/Portfolio)

## DESIGN
High-level architecture (Modules & Adapters + Hooks)

### GENERAL WORKFLOW
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Orchestration (Dagster)                                                  │
│ • Sensor: ingest_new_documents_sensor  ──► ingest_new_documents_job      │
│ • Sensor: split_new_docs_into_sentences_and_persist_sensor ─► split job  │
│ • Schedule: analyse_new_sentences_sentiment_schedule ─► analyse job      │
└──────────────┬───────────────────────────────┬───────────────────────────┘
               │                               │
               ▼                               ▼
      ┌───────────────────────┐        ┌──────────────────────────────────┐
      │ ingest_add_document_op│        │ split_sentences_and_persist_op   │
      └───────────┬───────────┘        └───────────────┬──────────────────┘
                  │                                    │ sentences[]
                  ▼                                    ▼
        ┌───────────────────────────────┐     ┌──────────────────────────────┐
        │ Persistence (SQLModel/SQLite) │     │ Persistence (SQLModel/SQLite)│
        │ • session.get_async_session   │     │ • SentenceRepository         │
        │ • DocumentRepository          │     │ • SentenceEntity             │
        │ • DocumentEntity              │     │ • app.db                     │
        │ • app.db                      │     └───────────────┬──────────────┘
        └───────────────────────────────┘                     │ get_unprocessed()
                                                              │ triggered by a sensor 
                                                              │ on "sentences" table
                                                              ▼
                                                   ┌──────────────────────────────┐
                                                   │ analyse_new_sentences_..._op │
                                                   └───────────────┬──────────────┘
                                                                   │ sentiments & confidences
                                                                   ▼
                                                   ┌──────────────────────────────┐
                                                   │ Persistence (SQLModel/SQLite)│
                                                   │ • SentenceSentimentRepository│
                                                   │ • SentenceSentimentEntity    │
                                                   └───────────────┬──────────────┘
                                                                   │ per sentence
                                                                   ▼
                                                   ┌────────────────────────────────┐
                                                   │ Tasks / LLM layer              │
                                                   │ • tasks.sentiment_analysis     │
                                                   │ • GenericLLMTask               │
                                                   │    │                           │
                                                   │    ▼                           │
                                                   │ LLMClient (runner)             │
                                                   │  • BEFORE HOOKS                │
                                                   │  • Adapter (e.g. Anthropic)    │
                                                   │  • AFTER HOOKS                 │
                                                   └───────────────┬────────────────┘
                                                                   │ normalized dict
                                                                   ▼
                                                   ┌───────────────────────────────┐
                                                   │ Persist sentiment result      │
                                                   │ • SentenceSentimentRepository │
                                                   │ • app.db                      │
                                                   └───────────────────────────────┘
                           
                           
┌──────────────────────────────────────────────────────────────────────────┐
│ LLM Package                                                              │
│ profiles.toml ─► ProfileStore ─► LLMClient                               │
│    BEFORE HOOKS ─► Adapter (e.g. Anthropic) ─► AFTER HOOKS               │
│                                                                          │
│    BEFORE HOOKS:                                                         │
│    • hooks.log (Loguru)                                                  │
│                                                                          │
│    AFTER HOOKS include:                                                  │
│    • hooks.langfuse (Langfuse SDK)                                       │
│    • hooks.mongo (schemas.LLMCall ► MongoDB via db.py)                   │
│    • hooks.guard (Guardrails repair/validate)                            │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Configuration                           │
│ • ./.env (API keys)                     │
│ • ./config.py (URIs, ports, table name) │
│ • ./profiles.toml (LLM profiles/hooks)  │
│ • ./orch/dagster/config.json            │
└─────────────────────────────────────────┘ 
```

### LLM Workflow
```

┌───────────────────────────────┐
│           profiles.toml       │
│  • env -> profile, hookset    │
│  • profile -> provider, model │
└───────────────┬───────────────┘
                │ (reads)
                ▼
┌───────────────────────────────┐
│ llm/profiles.py (ProfileStore)│
│  • resolve(env) → {provider,  │
│    model, before/after hooks} │
└───────────────┬───────────────┘
                │ (constructs)
                ▼
┌───────────────────────────────┐
│ llm/client.py (LLMClient)     │
│  • holds adapter + hooks      │
│  • orchestrates send()        │
└───────────────┬───────────────┘
                │ (call)
                │ INPUT: messages, prompt
                ▼
          ┌─────────────────────┐
          │ BEFORE HOOKS        │
          │ (hooks.*)           │
          └─────────┬───────────┘
                    │ (e.g. loguru)
                    ▼
┌───────────────────────────────────────────┐
│ llm/adapters.py (e.g. AnthropicAdapter)   │
│  • INPUT: messages, temperature           │
│  • ACTION: call SDK                       │
│  • OUTPUT: normalized dict response       │
└───────────────┬───────────────────────────┘
                │ (attach response to payload)
                ▼
          ┌─────────────────────┐
          │ AFTER HOOKS         │
          │ (hooks.*)           │
          └─────────┬───────────┘
                    │ (e.g. mongo, langfuse, guard)
                    ▼
```

### SETUP
    brew update
    brew install python@3.12
    python3.12 --version ⇒ Python 3.12.11
    brew install poetry 
    poetry config virtualenvs.in-project true --local  
    poetry install
    poetry env info ⇒ Virtualenv Python:         3.12.11
    source .venv/bin/activate

### DEV
##### Introduce & install new dependency
    poetry add <new-lib>
##### Introduce Environment to VSCode Pylance
    poetry env info
    Cmd+Shift+P (macOS) → Python: Select Interpreter
##### langfuse Setup
    cd infra/langfuse
    cp .env.example .env
    docker compose up   (docker compose down)
##### testing
    poetry run pytest -v tests/test_persistence/test_add_document.py
##### cli dev
    % python3 persistence/scripts/add_document.py --json-path /<path-to-json>/<filename>.json
    % python3 tasks/sentiment_analysis.py 'I absolutely loved this movie, it was fantastic!'
    % python3 tasks/sentiment_analysis.py 'The restaurant is located on Main Street.'
    % python3 tasks/sentiment_analysis.py 'The customer service was terrible, I’ll never come back.'
##### DAGster
    % poetry run dagster dev -m orchestration.dagster



### NAMING CONVENTION
•	Packages: short, all lowercase, avoid underscores.
•	Modules: lowercase, underscores allowed for readability.
•	Classes: CapWords (PascalCase).
•	Functions/Methods: snake_case, leading underscore if private.
•	Variables: snake_case.
•	Constants: UPPER_CASE with underscores.
•	File names: lowercase, underscores if needed.
•	Abbreviation: _w_ is stand for _with_ in file names


### TECH STACK
- Language & Tooling
  - Python 3.12
  - Poetry (in-project virtualenv)
- Common Libraries
  - Pydantic v2 (data models & validation)
  - pydantic-settings (environment config)
  - AnyIO (async runtime)
  - Tenacity (retries with backoff)
  - Loguru <- hook
- LLM Layer
  - Adapters pattern (custom AnthropicAdapter, OpenAI Adapter, etc.)
  - Client (LLMClient:runner)
- Guarding & Repair
  - Guardrails (Pydantic schema repair/validation)  <- hook
- Observability
  - Langfuse SDK <- hook
- Persistence
  - SQLModel
  - SQLAlchemy
  - MongoDB <- hook
  - Pydantic schema (LLMCall) for insert validation
- Configuration
  - profiles.toml (profiles → provider/model, hooksets → before/after)
- Analytics package
  - DuckDB
  - Polars
- Orchestration
  - Dagster (sensors, schedules, multiprocess executor)

### Core components

- Configuration
  - profiles.toml: env → profile, hookset; profile → provider/model; hookset → before/after dotted paths.
  - llm/profiles.ProfileStore: loads TOML, imports hook callables from dotted paths.

- Runner
  - llm/runner.LLMClient:
    - Hook type: async def hook(payload: dict[str, Any]) -> None
    - send(): builds payload (messages, prompt, provider, model, temperature, output_model, trace_id=str(uuid4)), runs before hooks → adapter → attaches response → runs after hooks, returns response dict.

- Adapter
  - llm/adapters:
    - Single responsibility: turn messages + params into SDK call, normalize to a plain dict.
    - Network resilience: Tenacity retry on transient HTTP/timeouts (exponential backoff with jitter recommended).

- Hooks (observer pattern)
  - hooks.log: log_request, log_usage
  - hooks.mongo.mongo_insert:
    - Builds a record with provider/model/prompt/response and created_at=datetime.now(timezone.utc).
    - insert_call_mongo is sync; offloaded via anyio.to_thread.run_sync to avoid blocking the event loop.
    - Data is validated against schemas.LLMCall before insert. created_at is stored as BSON Date and shows as {"$date": "..."} in JSON viewers.
  - hooks.langfuse.langfuse_track:
    - No metadata blob; writes explicit fields only.
    - Creates a trace with a string trace_id and a generation attached to the same trace_id.
    - Fields: name (operation), model, input (prompt), output (LLM text), tags ["provider:...", "model:..."].
  - hooks.guard.guard_output:
    - If output_model (a Pydantic model class) is present, first tries JSON parse + Pydantic validate.
    - Otherwise uses Guardrails (Guard.for_pydantic) to repair.
    - Only overwrites response text when the repaired output is valid JSON (or BaseModel); otherwise leaves original text unchanged.

- Validation and parsing
  - tasks/base.GenericLLMTask:
    - Sends a single network request via LLMClient.
    - Extracts first JSON object from the assistant text and validates against the provided Pydantic model.
    - Retries are applied only to the parsing step (JSON extraction/parse), not the network call.
    - Callers may soft-fail at the task/CLI layer to keep batch runs going.

Resilience policies

- Network-layer retry: in adapter (e.g. AnthropicAdapter.send) using Tenacity; handles 429/5xx/timeout with exponential backoff.
- Validation-layer retry: in GenericLLMTask only around JSON parsing
- Hooks are best-effort: errors are logged and do not fail the main flow.

Observability

- Logging with loguru at key stages: prompt preview, token usage, hook outcomes.
- Langfuse:
  - trace: group for a logical call (uses string trace_id).
  - generation: single LLM call details (model/input/output/tags).
  - No metadata payload is sent; fields are explicit for clarity.
- Mongo:
  - LLMCall schema includes created_at with default_factory to ensure timestamps.
  - Insert uses model_dump(mode="python") so datetime stays a Python datetime and is stored as BSON Date.

Execution flow (concise)

1) ProfileStore resolves env → {provider, model, before_hooks, after_hooks}.
2) LLMClient builds payload and runs before hooks.
3) Adapter calls provider SDK; response is normalized to dict and attached to payload.
4) After hooks run (logging, Langfuse, Mongo, Guard).
5) Task parses/validates the response and returns a typed object (or soft-fails per caller policy).

Best practices applied

- Separation of concerns: adapter (I/O), runner (orchestration), hooks (side-effects), task (parsing/validation).
- Async-safe hooks: blocking DB calls offloaded to threads.
- Deterministic retries: network vs. parsing retries are separated; no amplification.
- Explicit trace handling: string trace_id propagated end-to-end.
- Strict-but-safe guard: never downgrades response unless it can guarantee valid JSON.

Extensibility

- Add providers by implementing a new Adapter and mapping via profiles.toml.
- Add side-effects by registering new dotted-path hooks in hooksets.
- Add tasks by composing prompts and Pydantic models; reuse GenericLLMTask for send/validate.