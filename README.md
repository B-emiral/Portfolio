[https://github.com/B-emiral/Portfolio](https://github.com/B-emiral/Portfolio)

# DESIGN
High-level architecture (Modules & Adapters + Hooks)

### LLM Package
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
│ runner.LLMClient              │
│  • holds adapter + hooks      │
│  • orchestrates send()        │
└───────────────┬───────────────┘
                │ (call)
                │ INPUT: messages, prompt
                ▼
          ┌─────────────────────┐
          │ BEFORE HOOKS        │
          │ (llm.hooks.*)       │
          └─────────┬───────────┘
                    │
                    ▼
┌───────────────────────────────────────────┐
│ adapters.AnthropicAdapter                 │
│  • INPUT: messages, temperature           │
│  • ACTION: call Anthropic SDK             │
│  • OUTPUT: normalized dict response       │
└───────────────┬───────────────────────────┘
                │ (attach response to payload)
                ▼
          ┌─────────────────────┐
          │ AFTER HOOKS         │
          │ (llm.hooks.*)       │
          └─────────┬───────────┘
                    │ (e.g. mongo, langfuse, guard)
                    ▼
        ┌──────────────────────────┐
        │ schemas.LLMCall          │
        │  • validate payload      │
        └──────────┬───────────────┘
                   │ (insert)
                   ▼
        ┌──────────────────────────┐
        │ db.py (MongoDB)          │
        │  • insert_one()          │
        └──────────────────────────┘
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
- Core Libraries
  - Pydantic v2 (data models & validation)
  - pydantic-settings (environment config)
  - AnyIO (async runtime)
  - Tenacity (retries with backoff)
  - Loguru (hook)
- LLM Layer
  - Ports & Adapters pattern (custom AnthropicAdapter, OpenAI Adapter, etc.)
  - Runner (LLMClient)
- Guarding & Repair
  - Guardrails (Pydantic schema repair/validation)  <- hook
- Observability
  - Langfuse SDK <- hook
- Persistence
  - MongoDB <- hook
  - Pydantic schema (LLMCall) for insert validation
- Configuration
  - profiles.toml (profiles → provider/model, hooksets → before/after)
- Analytics package
  - DuckDB
  - Polars
- Data package
  - SQLModel
  - SQLAlchemy


### Core components

- Configuration
  - profiles.toml: env → profile, hookset; profile → provider/model; hookset → before/after dotted paths.
  - llm/profiles.ProfileStore: loads TOML, imports hook callables from dotted paths.

- Runner
  - llm/runner.LLMClient:
    - Hook type: async def hook(payload: dict[str, Any]) -> None
    - send(): builds payload (messages, prompt, provider, model, temperature, output_model, trace_id=str(uuid4)), runs before hooks → adapter → attaches response → runs after hooks, returns response dict.

- Adapter
  - llm/adapters.AnthropicAdapter:
    - Single responsibility: turn messages + params into Anthropic SDK call, normalize to a plain dict.
    - Network resilience: Tenacity retry on transient HTTP/timeouts (exponential backoff with jitter recommended).

- Hooks (observer pattern)
  - llm.hooks.log: log_request, log_usage
  - llm.hooks.mongo.mongo_insert:
    - Builds a record with provider/model/prompt/response and created_at=datetime.now(timezone.utc).
    - insert_call_mongo is sync; offloaded via anyio.to_thread.run_sync to avoid blocking the event loop.
    - Data is validated against schemas.LLMCall before insert. created_at is stored as BSON Date and shows as {"$date": "..."} in JSON viewers.
  - llm.hooks.langfuse.langfuse_track:
    - No metadata blob; writes explicit fields only.
    - Creates a trace with a string trace_id and a generation attached to the same trace_id.
    - Fields: name (operation), model, input (prompt), output (LLM text), tags ["provider:...", "model:..."].
  - llm.hooks.guard.guard_output:
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

- Network-layer retry: in adapter (AnthropicAdapter.send) using Tenacity; handles 429/5xx/timeout with exponential backoff.
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