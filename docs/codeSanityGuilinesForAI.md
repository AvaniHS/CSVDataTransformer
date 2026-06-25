# Core AI Instruction Set: Architecture, Code Quality, Error Handling & Logging

You are an expert systems architect and principal backend engineer. Your task is to build **csv_data_transformer** — a configuration-driven, API-first CSV transformation engine. You must strictly adhere to the following software engineering principles for all generated code, file layouts, and structural logic.

**Authoritative references:** `docs/REQUIREMENTS.md`, `sampleConfig.json`

---

## 1. Code Organization & Modularity

* **Folder hierarchy:** Organize code into logical domain directories per `docs/REQUIREMENTS.md` §3.4 (e.g., `config/`, `io/`, `engine/`, `pipeline/`, `api/`, `audit/`). Monolithic single-file layers are prohibited.
* **Pluggable & modular architecture:** Components must be fully decoupled. The config reader must not know pandas internals. The API layer must not contain transform logic — it delegates to the orchestrator.
* **Small building blocks:** Write focused, atomic functions. Complex workflows orchestrate smaller, testable units.
* **Extensibility:** Adding a new file format (XLSX) or config format (YAML) requires only a new class implementing the existing ABC — zero edits to orchestration.

---

## 2. Structural Design Patterns & SOLID Principles

* **SOLID compliance:** All five principles are mandatory.
* **Single Responsibility (SRP):** Config parsing, filesystem I/O, expression evaluation, and HTTP handling live in separate modules. A validator must not write CSV files.
* **Interface-driven development:** Depend on ABCs (`ConfigReader`, `DataReader`, `DataTargetWriter`, `ExecutionEngine`), not concrete classes.
* **Design patterns:**
  * **Factory** — `ConfigReaderFactory`, `DataReaderFactory`, `DataTargetFactory`
  * **Strategy** — `PandasExecutionEngine` behind `ExecutionEngine`
* **Type hints:** All public functions and class methods must have complete type annotations.

---

## 3. Error Handling (Fail-First)

This project uses a **fail-first** model. Do **not** implement row-level continue, dead-letter files, or silent coercion that hides errors. Any validation or transform failure aborts the entire run immediately.

### 3.1 Validation Gates

Implement and respect these gates in order. Abort on first failure; do not proceed to the next gate.

| Gate | Phase | Abort when |
|---|---|---|
| **G0** | Schema | Config JSON invalid, missing fields, duplicate aliases, unknown operators, broken references |
| **G1** | Pre-flight I/O | Source file missing, exceeds `max_file_size_mb`, target file exists and is non-empty, unreferenced uploads |
| **G2** | Post-extract | Root file empty (unless explicitly allowed in future) |
| **G3** | Post-transform | Silent all-null columns on non-nullable mappings |
| **G4** | Pre-write | Any `is_nullable: false` column contains null/NaN |
| **G5** | Post-write | Output file missing or row count mismatch |

### 3.2 Domain Exceptions

* Define all project-specific errors in `exceptions.py` — never raise bare `Exception` or generic `ValueError` from business logic.
* Use a small, explicit hierarchy. Example:

```python
class TransformerError(Exception):
    """Base error for all domain failures."""

class ConfigValidationError(TransformerError):
    gate: str  # e.g. "G0"

class PipelineError(TransformerError):
    gate: str
    blueprint_id: str | None

class TransformError(PipelineError):
  expression: str | None
  phase: str  # e.g. "derivations", "mappings"
```

* Every raised domain exception must carry enough context for logging and API responses: `gate`, `blueprint_id`, `migration_id` where applicable.

### 3.3 Exception Handling Rules

| Rule | Requirement |
|---|---|
| **Never swallow errors** | No bare `except:`, no `except Exception: pass` |
| **Catch narrowly** | Catch specific exceptions at boundaries (I/O, pandas eval, API handlers) |
| **Re-raise with context** | Wrap low-level errors: `raise TransformError(...) from exc` |
| **No silent fallbacks** | Do not substitute default values on cast failure unless `default_value` is explicitly configured in the mapping |
| **Cleanup in `finally`** | API workspace temp directories must be deleted in `finally`, including on failure |
| **Atomic writes** | Write to `{filename}.tmp`, then rename. Delete temp file on failure |
| **Blueprint abort** | If blueprint *N* fails, do not run blueprint *N+1* |

### 3.4 API Error Responses

Map domain exceptions to structured JSON — never return a raw stack trace to the client.

```json
{
  "error": "validation_failed",
  "message": "Human-readable description",
  "gate": "G0",
  "blueprint_id": "bp_direct_one_source_one_target",
  "details": []
}
```

| HTTP status | When |
|---|---|
| `400` | G0 failure, missing files, filename mismatch |
| `413` | File exceeds `max_file_size_mb` |
| `422` | G2–G4 transform or nullable violation |
| `500` | Unexpected internal error (log full traceback server-side only) |

### 3.5 Expression & Transform Errors

When a filter, join, derivation, or mapping fails:

1. Abort immediately — do not skip rows or columns.
2. Include in the error: `blueprint_id`, pipeline phase, expression text (if applicable), and column name.
3. Use safe parsers (`pd.to_numeric(..., errors='raise')` or explicit checks) — prefer fail-fast over `errors='coerce'` unless the requirement explicitly calls for coercion.

### 3.6 What NOT to Do

* Do not continue processing after a cast failure on a non-nullable column.
* Do not write partial output files on failure.
* Do not log an error and return success.
* Do not use bare Python `eval()` on config expressions.

---

## 4. Logging & Auditing

### 4.1 Logger Setup

* Configure logging once in `audit/logger.py`.
* Use Python stdlib `logging` — no `print()` in production code paths.
* Support `--log-level` (CLI) and server-level log level (API).

**Format (mandatory):**

```
[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s
```

### 4.2 Contextual Fields

Include these in log messages wherever practical:

| Field | Source |
|---|---|
| `migration_id` | Config top-level |
| `client_id` | Config top-level |
| `blueprint_id` | Current blueprint |
| `gate` | Current validation gate (when applicable) |

Prefer structured message text:  
`migration_id=mig_demo blueprint_id=bp_direct_one_source_one_target rows_before=1000 rows_after=850`

### 4.3 Required Checkpoint Logs

Log at **INFO** on every successful checkpoint. Log at **ERROR** before raising on failure.

| Checkpoint | Log |
|---|---|
| G0 pass | Blueprint count, connection refs resolved |
| After extract | Root file row count, file size (MB) |
| After each filter | Rows before, rows after, rows removed |
| After each join | Row count, join type, join alias |
| After derivations | Number of derivations completed |
| After mappings | Target column count, output row count |
| Before load | Final row count, target path |
| After load (G5) | Bytes written, elapsed time (ms) |

### 4.4 Log Levels

| Level | Use for |
|---|---|
| `DEBUG` | Expression translation, column name resolution, workspace paths |
| `INFO` | Checkpoint metrics, pipeline start/end, file names |
| `WARNING` | Recoverable anomalies that still pass validation (rare in v1) |
| `ERROR` | Gate failure, transform abort — always followed by raised exception |

### 4.5 API Response Headers (Supplement to Logs)

On successful `/transform` responses, include:

| Header | Value |
|---|---|
| `X-Migration-Id` | `migration_id` from config |
| `X-Row-Count-{blueprint_id}` | Final row count per blueprint |
| `X-Elapsed-Ms` | Total processing time |

### 4.6 Logging Rules for AI-Generated Code

* Every public pipeline step (`extract`, `filter`, `join`, `derive`, `map`, `load`) must emit at least one INFO checkpoint log.
* Log the start and end of each blueprint run.
* On exception: log at ERROR with `gate`, `blueprint_id`, and a concise message **before** re-raising.
* Do not log full file contents or sensitive data — log file names, row counts, and column names only.
* Use a single logger per module: `logger = logging.getLogger(__name__)`.

---

## 5. Performance & Safety Constraints

* **File size guard:** Enforce `max_file_size_mb` from connection `file_options` before reading — abort at G1 if exceeded.
* **Target emptiness:** Target CSV must be absent or zero bytes before write — abort at G1/G4 if not.
* **In-memory processing (v1):** Pandas in-memory transforms are acceptable within file size limits. Do not introduce chunking unless explicitly required in a future spec.
* **Idempotent writes:** Re-running against an empty target produces a full overwrite — never append or merge into existing target data.
* **Workspace isolation:** Each API request uses its own temp directory. No shared mutable state between requests.

---

## 6. Testing Expectations for Error & Log Paths

* Unit tests must assert that invalid config raises `ConfigValidationError` at G0.
* Unit tests must assert missing source files fail at G1.
* Unit tests must assert nullable violations fail at G4 before any write occurs.
* API tests must assert error JSON shape (`error`, `message`, `gate`) and correct HTTP status codes.
* Do not add tests that expect row-level continue or dead-letter behavior — fail-first is the contract.

---

## 7. API Structure & Swagger Conventions

All HTTP code lives under `api/`. Route handlers are thin — parse request, call orchestrator, return response.

### 7.1 Module Layout (mandatory)

```
api/
├── app.py                  # create_app() only — no business logic
├── dependencies.py
├── middleware.py
├── exception_handlers.py
├── schemas/                # OpenAPI DTOs — NOT pipeline config models
├── routes/
│   ├── health.py
│   └── transform.py
├── workspace.py
└── responses.py
```

* Pipeline config models → `config/models.py`
* API request/response DTOs → `api/schemas/` (used for `response_model` and Swagger)

### 7.2 Swagger / OpenAPI Requirements

* Configure `docs_url`, `redoc_url`, `openapi_url` under `/api/v1/` prefix.
* Set `title`, `description`, `version`, and `openapi_tags` on the FastAPI instance.
* Every JSON endpoint must declare `response_model`.
* Every endpoint must have `tags`, `summary`, and `operation_id`.
* File-download endpoints (`/transform`) must document `200` responses for `text/csv` and `application/zip` plus all `ErrorResponse` error codes in `responses={}`.
* Register domain exception handlers that return `ErrorResponse` — never leak stack traces.

### 7.3 Documentation URLs (must work after startup)

| URL | Purpose |
|---|---|
| `http://localhost:8000/api/v1/docs` | Swagger UI |
| `http://localhost:8000/api/v1/redoc` | ReDoc |
| `http://localhost:8000/api/v1/openapi.json` | OpenAPI schema |

### 7.4 API Coding Rules

* No pandas imports in `api/routes/` or `api/schemas/`.
* Use `UploadFile` from FastAPI for multipart file inputs.
* Always cleanup workspace in `try/finally`.
* Return `JSONResponse` for errors, `FileResponse` / `StreamingResponse` for CSV/ZIP success.
* Add `X-Request-Id` header via middleware for traceability.
