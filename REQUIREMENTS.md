# CSV Data Transformer

## Document Status

| Field | Value |
|---|---|
| Version | 1.6 |
| Last updated | 2026-06-25 |
| Source inputs | `rawRequirements.txt`, `sampleConfig.json` |
| Status | **Finalized** |

---

## 1. System Overview

**CSV Data Transformer** (`csv_data_transformer`) is a pluggable, local-first data transformation engine written in **Python**, exposed primarily as a **REST API**. The system:

1. Accepts a JSON config and source data files via HTTP.
2. Validates the full configuration before any data operation.
3. Extracts data from uploaded CSV files referenced by the config.
4. Performs relational operations (joins, filters, column derivations) in memory using **Pandas**.
5. Returns **one or more transformed CSV files** in the HTTP response.

### 1.1 Primary Use Cases (v1)

Each blueprint produces **one target CSV**. A config may define **one or more blueprints**, so a single API request can return one or multiple output files.

| Use case | Source files | Blueprints | Output |
|---|---|---|---|
| **A — Single-file transform** | 1 CSV | 1 | **1** target CSV |
| **B — Multi-file join & transform** | 2+ CSVs (joined in one blueprint) | 1 | **1** target CSV |
| **C — Multiple outputs (different sources)** | 2+ CSVs across blueprints | 2+ | **2+** target CSVs |
| **D — Single source split** | **Same 1 CSV** for all blueprints | 2+ | **2+** target CSVs (column subsets + per-blueprint transforms) |

**Use case A:** Upload `orders.csv` only. No joins. Filters, derivations, mappings → one output.

**Use case B:** Upload `customer_master.csv` + `geo_address_mapping.csv`. Join in one blueprint → one output.

**Use case C:** Each blueprint uses its own source set. Example: full `sampleConfig.json` with 2 blueprints → ZIP with 2 outputs.

**Use case D — single source split into multiple targets:** Upload **one** CSV (e.g. `orders.csv`). Config defines **two or more blueprints** that all read the same root file. Each blueprint has its own `sequence_order`, filters, derivations, column mappings, and target file — selecting different columns and applying different transforms per output.

> One request = one config = **1..N blueprints** = **1..N target CSVs**. Blueprints are **fully independent pipelines** — they may share the same source file(s) or use different ones.

### 1.2 Core Architecture Goals

| Goal | Description |
|---|---|
| Zero database dependency (current phase) | All `connection_ref` values resolve to a structured local directory containing source files. No external DB drivers in v1. |
| Fail-first at every phase | Config validation, I/O guards, transformation, and pre-write checks all abort immediately on failure — no partial writes, no silent skips. |
| Agentic code-generative friendliness | Highly structured, modular, type-hinted code with clear abstraction boundaries so AI agents can iterate on individual modules without regressions. |
| Extensibility without core edits | New file formats (XLSX, Parquet, YAML config) are added by implementing interfaces — orchestration code stays unchanged. |
| API-first delivery | Callers upload config + one or more data files; the service returns one or more transformed CSVs. No persistent storage required per request. |

### 1.3 Execution Modes

The same pipeline engine runs in two modes. The API is the **primary** interface; CLI is for local development and testing.

| Mode | Input | Output | Path resolution |
|---|---|---|---|
| **API** | HTTP multipart: config JSON + 1..N source CSV uploads | **1..M** transformed CSVs (file or ZIP) | Ephemeral per-request workspace (temp directory) |
| **CLI** | `--config` path on local filesystem | Files written to `target_path` in config | Paths from connection `base_path` / `target_path` |

In API mode, the service creates an isolated temp workspace per request, maps uploaded files into the workspace input directory by filename, runs the pipeline, and streams results back. The workspace is deleted after the response is sent.

### 1.4 Non-Goals (v1)

- Real-time streaming ingestion.
- Distributed execution (Spark, Dask).
- Row-level chunking / streaming reads (replaced by file-size guardrails).
- Database connectors — deferred to a future phase.
- UPSERT / APPEND / primary-key merge semantics (target CSV is always empty).
- Web UI / admin dashboard — API-only for v1.
- Long-lived async job queue — requests are synchronous per call (within timeout).

---

## 2. Configuration Model

Configuration is a single JSON document. The reference sample is **`sampleConfig.json`** — it demonstrates **direct mapping only** (no filters, derivations, or expressions) for the two most common patterns.

### 2.1 Top-Level Metadata

| Field | Required | Description |
|---|---|---|
| `$schema` | Recommended | JSON Schema URI for IDE validation and boot-time schema checks. |
| `migration_id` | Yes | Unique identifier for this migration run (logging, audit). |
| `client_id` | Yes | Tenant/client identifier (logging, audit). |
| `version` | Yes | Semantic version of the config document. |
| `connections` | Yes | Named connection definitions keyed by reference name. |
| `blueprints` | Yes | One or more transformation pipelines. Each blueprint produces exactly one target CSV. |

### 2.2 Connections

Each connection is keyed by a name referenced elsewhere via `connection_ref`.

**Supported type (v1):** `LOCAL_FILE_DIRECTORY`  
*(Alias accepted for backward compatibility: `LOCAL_CSV_DIRECTORY`)*

| Field | Required | Description |
|---|---|---|
| `type` | Yes | `LOCAL_FILE_DIRECTORY` |
| `base_path` | Yes | Directory containing source input files. |
| `target_path` | Yes | Directory where transformed output files are written. |
| `file_options` | No | Per-connection read/write options (see §2.2.1). Defaults applied when omitted. |

#### 2.2.1 Connection `file_options`

All options are configurable per connection to support future formats (e.g., XLSX).

| Field | Default | Description |
|---|---|---|
| `format` | `CSV` | Source/target file format. v1: `CSV`. Future: `XLSX`. |
| `encoding` | `utf-8` | File character encoding. |
| `delimiter` | `,` | Field delimiter (CSV). |
| `quote_char` | `"` | Quote character (CSV). |
| `header_row` | `true` | First row is column headers. |
| `max_file_size_mb` | `100` | Maximum allowed source file size. Exceeding this aborts before read. |

**Path resolution (CLI mode):**

- Source file path = `{base_path}/{file_name}`
- Target file path = `{target_path}/{file_name}`

**Path resolution (API mode):**

- Source file path = `{workspace}/input/{file_name}` — uploaded file must match `file_name` exactly.
- Target file path = `{workspace}/output/{file_name}` — always empty before write; never persisted after response.
- `base_path` and `target_path` in the config are **ignored** in API mode; the service injects the workspace paths.

### 2.3 Blueprints

Each blueprint defines one end-to-end pipeline: **one or more source CSVs in → exactly one target CSV out**.

Blueprints in the same config are **independent**. Multiple blueprints may reference the **same source file** (use case D — single source split) with different filters, derivations, and column mappings per blueprint.

| Field | Required | Description |
|---|---|---|
| `sequence_order` | Yes | Execution order among blueprints (ascending). Blueprint 1 runs fully before blueprint 2. |
| `blueprint_id` | Yes | Stable identifier for logging and error reporting. |
| `sources` | Yes | Root table and optional join definitions. |
| `target` | Yes | Single output file definition. |
| `pre_filters` | No | Filters applied before joins. Default: `[]`. |
| `derivations` | No | Sequential calculated variables. Default: `[]`. |
| `mappings` | Yes | Target column definitions. |
| `post_filters` | No | Filters applied after mapping. Default: `[]`. |

> **Removed from v1:** `chunking_strategy`, `primary_keys`, `on_conflict`.

#### 2.3.1 Sources — Root Table

Always required. For use case A (single-file transform), this is the **only** source file.

| Field | Required | Description |
|---|---|---|
| `connection_ref` | Yes | Key into `connections`. |
| `file_name` | Yes | Filename within the connection's `base_path`. Must match an uploaded file (API) or exist on disk (CLI). |
| `alias` | Yes | Short prefix identifying the source in expressions (e.g., `cm`, `ord`). Must be unique within the blueprint. |
| `comment` | No | Human-readable documentation only. |

#### 2.3.2 Sources — Joins (Optional)

`joins` is an array. **Omit or set to `[]` when only one CSV is provided** (use case A). Add one entry per additional CSV to merge (use case B). Joins run sequentially in array order.

| Field | Required | Description |
|---|---|---|
| `join_type` | Yes | `LEFT`, `INNER`, `RIGHT`, or `OUTER`. |
| `connection_ref` | Yes | Connection for the join table file. |
| `file_name` | Yes | Filename for the join table. |
| `alias` | Yes | Prefix for join table columns. Must be unique within the blueprint. |
| `conditions` | Yes | Non-empty array of join predicates and/or condition groups. |
| `comment` | No | Documentation only. |

**Join condition — predicate form:**

| Field | Required | Description |
|---|---|---|
| `left` | Yes | Qualified column reference, e.g. `cm.id`. |
| `operator` | Yes | See §2.5 — Supported Operators. |
| `right` | Conditional | Literal value or qualified column reference. Not required for `IS_NULL` / `IS_NOT_NULL`. |
| `right_type` | Conditional | `column` or `literal`. Required when `right` is present. |

**Join condition — group form (compound logic):**

| Field | Required | Description |
|---|---|---|
| `logic` | Yes | `AND` or `OR`. |
| `conditions` | Yes | Array of predicate or nested group objects. |

**Multi-condition default:** Top-level `conditions` array items are combined with **AND** when not wrapped in an explicit group.

#### 2.3.3 Target

| Field | Required | Description |
|---|---|---|
| `connection_ref` | Yes | Connection for output path resolution. |
| `file_name` | Yes | Output filename. |
| `comment` | No | Documentation only. |

**Target file policy:**

- Target file must **not exist**, or must be **empty** (zero bytes) before write.
- If the target file exists and contains data, the pipeline **aborts** (fail-first).
- Write mode is always **full overwrite** of the empty target file.
- No primary keys, UPSERT, or APPEND semantics.

#### 2.3.4 Filters

`pre_filters` and `post_filters` accept an array of **predicate objects**, **group objects**, or **expression objects**.

**Predicate form** (recommended for simple rules):

```json
{ "left": "cm.status", "operator": "==", "right": "ACTIVE", "right_type": "literal" }
```

**Group form** (compound logic):

```json
{
  "logic": "AND",
  "conditions": [
    { "left": "tih.invoice_date", "operator": ">=", "right": "2024-01-01", "right_type": "literal" },
    { "left": "tih.status", "operator": "IN", "right": ["POSTED", "PAID"], "right_type": "literal" }
  ]
}
```

**Expression form** (complex rules):

```json
{
  "type": "expression",
  "value": "(til__unit_price * til__quantity_billed) > 0 and tih__tax_exempt_flag != 1"
}
```

Expression strings use **physical column names** (`alias__column`). The engine translates config dot-notation (`alias.column`) to physical names before evaluation.

#### 2.3.5 Derivations

Sequential list. A variable created at step *N* is available at step *N+1*.

| Field | Required | Description |
|---|---|---|
| `variable_name` | Yes | Name in the `deriv` namespace (e.g., `formatted_phone`). |
| `transform_type` | Yes | `EXPRESSION`, `REGEXP_REPLACE`, or `CASE`. |
| `comment` | No | Documentation only. |

**`transform_type: EXPRESSION`**

| Field | Required |
|---|---|
| `expression` | Yes — pandas expression using `alias.column` or `deriv.variable_name` references. |

**`transform_type: REGEXP_REPLACE`**

| Field | Required |
|---|---|
| `source` | Yes — qualified column reference. |
| `pattern` | Yes — regex pattern string. |
| `replacement` | Yes — replacement string (may be empty). |

**`transform_type: CASE`**

| Field | Required |
|---|---|
| `branches` | Yes — array of `{ "when": <predicate or group>, "then": <literal or column ref or expression> }`. |
| `else` | No — fallback literal, column ref, or expression. |

**Reference in mappings:** `deriv.{variable_name}` (e.g., `deriv.formatted_phone`).

#### 2.3.6 Mappings

Each mapping produces one target column in the output CSV.

| Field | Required | Description |
|---|---|---|
| `target_column` | Yes | Output column name (unqualified — no alias prefix). |
| `source_type` | Yes | `DIRECT`, `DERIVED`, or `EXPRESSION`. |
| `source_value` | Yes | Column reference or expression depending on `source_type`. |
| `cast_to` | Yes | `str`, `int64`, `float64`, `datetime64[ns]`. |
| `is_nullable` | Yes | When `false`, any null/NaN after casting aborts the pipeline before write. |
| `default_value` | No | Literal fallback when source evaluates to null (applied before nullable check). |

| `source_type` | `source_value` semantics |
|---|---|
| `DIRECT` | Qualified source column, e.g. `cm.global_uuid`. |
| `DERIVED` | Derivation reference, e.g. `deriv.formatted_phone`. |
| `EXPRESSION` | Pandas expression, e.g. `gam.country_code.fillna('USA')`. |

#### 2.3.7 Direct Mapping Only (No Transformation)

When there is **no transformation** — only column selection, optional rename, and type cast — the config uses this minimal shape. See **`sampleConfig.json`**.

**Rules for direct-only configs:**

| Section | Value |
|---|---|
| `pre_filters` | `[]` (empty) |
| `derivations` | `[]` (empty) |
| `post_filters` | `[]` (empty) |
| `mappings[].source_type` | Always `DIRECT` |
| `mappings[].source_value` | Qualified column: `{alias}.{source_column}` |
| `cast_to` | Type alignment only (`str`, `int64`, `float64`, `datetime64[ns]`) — not a business transform |

**Pattern 1 — one source, one target**

```json
{
  "blueprint_id": "bp_direct_one_source_one_target",
  "sources": {
    "root_table": { "file_name": "employees.csv", "alias": "emp" },
    "joins": []
  },
  "pre_filters": [],
  "derivations": [],
  "post_filters": [],
  "target": { "file_name": "employees_export.csv" },
  "mappings": [
    { "target_column": "employee_id", "source_type": "DIRECT", "source_value": "emp.id", "cast_to": "str", "is_nullable": false },
    { "target_column": "email", "source_type": "DIRECT", "source_value": "emp.email", "cast_to": "str", "is_nullable": true }
  ]
}
```

Upload: `employees.csv` → Output: `employees_export.csv`

**Pattern 2 — two sources (join), one target**

Same as pattern 1, plus a `joins` entry. Mappings pull columns from both aliases after the join:

```json
{
  "blueprint_id": "bp_direct_two_sources_one_target",
  "sources": {
    "root_table": { "file_name": "employees.csv", "alias": "emp" },
    "joins": [
      {
        "join_type": "LEFT",
        "file_name": "departments.csv",
        "alias": "dept",
        "conditions": [
          { "left": "emp.department_id", "operator": "==", "right": "dept.id", "right_type": "column" }
        ]
      }
    ]
  },
  "pre_filters": [],
  "derivations": [],
  "post_filters": [],
  "target": { "file_name": "employees_with_department.csv" },
  "mappings": [
    { "target_column": "employee_id", "source_type": "DIRECT", "source_value": "emp.id", "cast_to": "str", "is_nullable": false },
    { "target_column": "department_name", "source_type": "DIRECT", "source_value": "dept.name", "cast_to": "str", "is_nullable": true }
  ]
}
```

Upload: `employees.csv` + `departments.csv` → Output: `employees_with_department.csv`

> When transforms are needed later, add `pre_filters`, `derivations` (`REGEXP_REPLACE`, `CASE`, `EXPRESSION`), or `mappings` with `source_type: DERIVED` / `EXPRESSION` — the same blueprint structure applies.

---

## 2.4 Column Naming Convention

Config uses **dot notation** for readability. The engine stores columns using **double-underscore** physical names — a widely used ETL convention (Spark, dbt, pandas merge suffixes).

| Context | Format | Example |
|---|---|---|
| Config reference | `{alias}.{column}` | `cm.status`, `til.unit_price` |
| Physical DataFrame column | `{alias}__{column}` | `cm__status`, `til__unit_price` |
| Derivation config reference | `deriv.{variable_name}` | `deriv.formatted_phone` |
| Physical derivation column | `deriv__{variable_name}` | `deriv__formatted_phone` |
| Target output column | `{target_column}` as declared | `company_name`, `tax_amount` |

**Rules:**

1. On read, prefix every source column with `{alias}__`.
2. After each join, prefix join-table columns with the join `alias`.
3. All expression translation replaces `alias.column` → `` `alias__column` `` before evaluation.
4. Target mappings produce a **new** DataFrame with only `target_column` names (no alias prefix).
5. Aliases must be unique within a blueprint. Duplicate aliases fail config validation.

---

## 2.5 Supported Operators

Used in join conditions, filter predicates, and CASE `when` branches.

| Operator | Aliases | Description | `right` required |
|---|---|---|---|
| `==` | `=`, `EQ` | Equal | Yes |
| `!=` | `<>`, `NE` | Not equal | Yes |
| `<` | `LT` | Less than | Yes |
| `<=` | `LE` | Less than or equal | Yes |
| `>` | `GT` | Greater than | Yes |
| `>=` | `GE` | Greater than or equal | Yes |
| `IN` | | Value in list | Yes (array literal) |
| `NOT_IN` | `NOT IN` | Value not in list | Yes (array literal) |
| `LIKE` | | SQL-style pattern (`%`, `_`) | Yes |
| `NOT_LIKE` | `NOT LIKE` | Negated pattern match | Yes |
| `IS_NULL` | `IS NULL` | Value is null/NaN | No |
| `IS_NOT_NULL` | `IS NOT NULL` | Value is not null | No |

**`right_type` values:**

| Value | Meaning |
|---|---|
| `literal` | `right` is a constant (string, number, boolean, or array for `IN`). |
| `column` | `right` is a qualified column reference (`alias.column`). |

---

## 3. Architectural Design Patterns & SOLID Compliance

### 3.1 Factory Method Pattern

| Factory | Responsibility |
|---|---|
| `ConfigReaderFactory` | Instantiates a `ConfigReader` by file extension (`.json` → `JsonConfigReader`). |
| `DataReaderFactory` | Instantiates a `DataReader` by connection `file_options.format` (`CSV` → `CsvDataReader`; future `XLSX` → `XlsxDataReader`). |
| `DataTargetFactory` | Instantiates a `DataTargetWriter` by connection format. |

### 3.2 Strategy Pattern — Transformation Framework

| Component | Role |
|---|---|
| `ExecutionEngine` (ABC) | Generic interface for DataFrame mutations. |
| `PandasExecutionEngine` | Concrete strategy implementing filters, joins, derivations, mappings. |

**Constraint:** Orchestration logic must **not** contain inline pandas code. All mutations delegate to the engine strategy.

### 3.3 SOLID Enforcement

| Principle | Requirement |
|---|---|
| **SRP** | Config parsing, filesystem I/O, and DataFrame evaluation live in separate classes. |
| **OCP** | Adding XLSX, Parquet, or YAML config requires only new class files — zero orchestrator edits. |
| **LSP** | All concrete readers/writers/engines honor their ABC contracts. |
| **ISP** | Focused interfaces; no unused abstract methods. |
| **DIP** | Pipeline managers depend on ABCs, not concrete classes. |

### 3.4 Module Layout

```
csv_data_transformer/
├── __init__.py
├── __main__.py                  # CLI entry point (dev / local use)
├── api/
│   ├── app.py                   # FastAPI factory, OpenAPI metadata, router registration
│   ├── dependencies.py          # Shared DI (settings, orchestrator)
│   ├── middleware.py            # Request ID, timing headers
│   ├── exception_handlers.py    # Domain exception → JSON error mapping
│   ├── schemas/                 # Pydantic models for OpenAPI (request/response DTOs)
│   │   ├── errors.py            # ErrorResponse
│   │   ├── health.py            # HealthResponse
│   │   └── validate.py          # ValidateResponse
│   ├── routes/
│   │   ├── health.py            # GET /api/v1/health
│   │   └── transform.py         # POST /api/v1/transform, POST /api/v1/validate
│   ├── workspace.py             # Ephemeral per-request temp directory manager
│   └── responses.py             # File / ZIP response builders
├── config/
│   ├── models.py                # Typed config dataclasses / Pydantic models
│   ├── base.py                  # ConfigReader ABC
│   ├── json_reader.py           # JsonConfigReader
│   └── factory.py               # ConfigReaderFactory
├── connections/
│   ├── base.py                  # Connection model types
│   └── local_file.py            # LOCAL_FILE_DIRECTORY resolver
├── io/
│   ├── readers/
│   │   ├── base.py              # DataReader ABC
│   │   ├── csv_reader.py        # CsvDataReader
│   │   └── factory.py           # DataReaderFactory
│   └── writers/
│       ├── base.py              # DataTargetWriter ABC
│       ├── csv_writer.py        # CsvDataWriter
│       └── factory.py           # DataTargetFactory
├── engine/
│   ├── base.py                  # ExecutionEngine ABC
│   ├── pandas_engine.py         # PandasExecutionEngine
│   ├── column_names.py          # alias.column ↔ alias__column translation
│   ├── operators.py             # Operator dispatch for predicates
│   └── expressions.py           # Expression parsing / CASE / REGEXP_REPLACE
├── pipeline/
│   ├── validator.py             # Config + pre-flight validation
│   ├── orchestrator.py          # Blueprint sequencing
│   └── blueprint_runner.py      # Single-blueprint ETL flow
├── audit/
│   └── logger.py                # Structured logging setup
└── exceptions.py                # Domain-specific errors
schema/
└── config.schema.json           # JSON Schema for config validation
tests/
├── unit/
├── integration/
└── fixtures/                    # Sample CSV + config files
data/
├── input/                       # Source fixture CSVs
└── output/                      # Target output (empty before runs)
```

---

## 4. Data Pipeline Processing Flow

For every blueprint, execute **sequentially** in this exact order:

```
[Validate Config & Pre-Flight] → [Extract Root] → [Pre-Filters] → [Sequential Joins (if any)]
  → [Derivations] → [Mappings & Casts] → [Post-Filters] → [Target Verification] → [Load]
```

Each blueprint runs this flow independently. When `sources.joins` is empty, the **Sequential Joins** step is skipped.

When a config defines multiple blueprints, repeat the full flow per blueprint (in `sequence_order`). Source files may be reused across blueprints; each blueprint writes to its own target file.

### 4.1 Validation Gates (Fail-First)

| Gate | When | Checks |
|---|---|---|
| **G0 — Config schema** | Before any blueprint | JSON Schema, required fields, unique aliases, valid operators, mapping completeness. |
| **G1 — Pre-flight I/O** | Before each blueprint extract | Source files exist, within `max_file_size_mb`, readable. Target file absent or empty. |
| **G2 — Post-extract** | After root read | Root file not empty unless blueprint explicitly allows (future flag). Log row count. |
| **G3 — Post-transform** | After derivations/mappings | No silent all-null columns for non-nullable mappings. |
| **G4 — Pre-write** | Before load | All `is_nullable: false` columns contain zero nulls. Target still empty/absent. |
| **G5 — Post-write** | After load | Output file exists, row count matches expectation, log final metrics. |

Any gate failure **aborts the entire run** immediately. Subsequent blueprints do not execute.

### 4.2 Step Details

| Step | Action |
|---|---|
| **1. Extract Root** | Read root file with connection `file_options`. Prefix columns as `{alias}__{column}`. |
| **2. Pre-Filters** | Apply each filter entry (predicate, group, or expression). Abort on evaluation error. |
| **3. Sequential Joins** | If `joins` is non-empty: load each join file, prefix columns, merge using `join_type` and conditions. If empty: skip. |
| **4. Derivations** | Evaluate each derivation in order. Store as `deriv__{variable_name}`. |
| **5. Mappings & Casts** | Build target DataFrame. Apply defaults, evaluate expressions, cast types. Abort on cast failure. |
| **6. Post-Filters** | Apply post-mapping filters. |
| **7. Load** | Atomic write to target path (temp file → rename). |

### 4.3 Multi-Blueprint Execution

- Process all blueprints in ascending `sequence_order` (API and CLI).
- Each blueprint is an **independent pipeline**: own filters, derivations, mappings, and **one** target CSV.
- **Same source, multiple targets (use case D):** two or more blueprints may use the identical `root_table.file_name` (and identical joins). Each blueprint re-reads the source and applies its own transform logic. Outputs differ by design — e.g. blueprint 1 selects summary columns, blueprint 2 selects line-detail columns.
- Source files shared across blueprints are uploaded once; each blueprint reads from the same workspace input path on its own run.
- **Fail-first:** any blueprint failure aborts all remaining blueprints.
- **G1 file resolution:** collect the union of all unique `file_name` values across every blueprint (root + joins). Upload must satisfy this deduplicated set.

---

## 5. Expression & Transform Evaluation

### 5.1 Design Choice — Hybrid Config Pattern

| Construct | Simple case | Complex case |
|---|---|---|
| Filters | Predicate / group objects | `type: expression` string |
| Derivations | `REGEXP_REPLACE`, `CASE` structured types | `transform_type: EXPRESSION` |
| Mappings | `DIRECT`, `DERIVED` | `source_type: EXPRESSION` |

Structured types are preferred for readability and validation. Expression strings are available when structured forms are insufficient.

### 5.2 Expression Translation

Config dot-notation is translated before evaluation:

```
cm.status           →  cm__status
deriv.formatted_phone  →  deriv__formatted_phone
til.unit_price * til.quantity_billed  →  til__unit_price * til__quantity_billed
```

**Basic math:** `pd.eval()` / column arithmetic on physical names.

**RegEx (`REGEXP_REPLACE` derivation type):**

```python
df["deriv__formatted_phone"] = df["cm__phone_raw"].str.replace(pattern, replacement, regex=True)
```

**Conditional (`CASE` derivation type):**

```python
np.where(<when_predicate>, <then_value>, <else_value>)
```

Nested CASE branches compile to nested `np.where()` calls.

### 5.3 Expression Safety

- Use `df.query()` / `pd.eval()` with explicit namespaces — never bare Python `eval()`.
- Reject expressions containing dunder attributes, imports, or semicolons.
- Include `blueprint_id`, expression text, and phase in all error messages.

---

## 6. Write Semantics

| Rule | Behavior |
|---|---|
| Target precondition | File must not exist, or must be 0 bytes. |
| Write mode | Full overwrite (create new file). |
| Atomicity | Write to `{file_name}.tmp`, then rename to `{file_name}`. |
| Column order | Matches `mappings` declaration order. |
| Header | Always written on new file. |
| Encoding/delimiter | Taken from connection `file_options`. |

---

## 7. Error Handling & Auditing

### 7.1 Fail-First Model

All three phases abort on first error:

| Phase | Behavior |
|---|---|
| **Schema** | Validate config (G0) before touching any data file. |
| **I/O** | Validate file existence, size, target emptiness (G1). Abort before read/write. |
| **Transform** | Any filter/join/derivation/mapping/cast error aborts the blueprint and the run. No row-level continue. |
| **Pre-write** | Nullable violations abort before any bytes are written to the target. |

### 7.2 Logging

**Format:**

```
[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s
```

**Required checkpoint metrics:**

| Checkpoint | Metric |
|---|---|
| G0 pass | Config valid — blueprint count, connection refs resolved. |
| After extract | Root file row count, file size MB. |
| After each filter | Rows before / after, rows removed. |
| After each join | Row count, join type, join alias. |
| After derivations | Derivation count completed. |
| After mappings | Target column count, rows in output frame. |
| Before load | Final row count, target path. |
| After load | Bytes written, elapsed time. |

Each log line should include `migration_id`, `blueprint_id`, and `client_id` where practical.

---

## 8. REST API Interface (Primary)

Built with **FastAPI**. Default bind: `0.0.0.0:8000`.

### 8.1 Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/transform` | Validate config, run all blueprints, return transformed CSV file(s). |
| `POST` | `/api/v1/validate` | Validate config and uploaded files only — no transform, no output files. |
| `GET` | `/api/v1/health` | Liveness check. Returns `{ "status": "ok" }`. |

### 8.2 `POST /api/v1/transform`

**Request:** `multipart/form-data`

| Part | Required | Description |
|---|---|---|
| `config` | Yes | JSON config with one or more blueprints. Same schema as `sampleConfig.json`. |
| `files` | Yes | Source CSV files required by **all** blueprints (deduplicated by filename). Each upload filename must match a `file_name` referenced in any blueprint. |

**Processing flow:**

1. Parse and validate config (G0).
2. Create ephemeral workspace temp directory.
3. Save uploaded files to `{workspace}/input/` keyed by original filename.
4. Verify all required source files are present and within `max_file_size_mb` (G1):
   - Collect every unique `file_name` from all blueprints (each root table + each join).
   - Reject if any required file is missing or if an uploaded file is not referenced by any blueprint.
5. Run all blueprints in `sequence_order` against workspace paths (API mode).
6. Collect all output files from `{workspace}/output/`.
7. Return transformed file(s) (see below).
8. Delete workspace temp directory (always, including on error).

**Required files:** union of all source `file_name` values across every blueprint in the config.

**Success response:**

| Blueprints in config | HTTP status | Response |
|---|---|---|
| 1 | `200 OK` | Single CSV (`Content-Type: text/csv`, `Content-Disposition: attachment; filename="{target.file_name}"`). |
| 2+ | `200 OK` | ZIP archive (`Content-Type: application/zip`, `Content-Disposition: attachment; filename="transformed_outputs.zip"`) containing each blueprint's target CSV named by `target.file_name`. |

**Response headers (all success responses):**

| Header | Description |
|---|---|
| `X-Migration-Id` | From config `migration_id`. |
| `X-Row-Count-{blueprint_id}` | Final row count per blueprint (e.g., `X-Row-Count-bp_customer_profiles: 1523`). |
| `X-Elapsed-Ms` | Total processing time in milliseconds. |

**Error response:** `4xx` / `5xx` with JSON body:

```json
{
  "error": "validation_failed",
  "message": "Human-readable description",
  "gate": "G0",
  "blueprint_id": "bp_customer_profiles",
  "details": []
}
```

| HTTP status | When |
|---|---|
| `400` | Config schema invalid (G0), missing uploaded files, filename mismatch, unreferenced uploads. |
| `413` | Uploaded file exceeds `max_file_size_mb`. |
| `422` | Transform error — filter/join/derivation/mapping/cast failure (G2–G4). |
| `500` | Unexpected internal error. |

### 8.3 `POST /api/v1/validate`

Same request format as `/transform`. Runs G0 + G1 only.

**Success response:** `200 OK`

```json
{
  "valid": true,
  "migration_id": "mig_direct_mapping_demo_2026",
  "blueprint_count": 2,
  "output_files": ["employees_export.csv", "employees_with_department.csv"],
  "required_files": ["employees.csv", "departments.csv"],
  "uploaded_files": ["employees.csv", "departments.csv"]
}
```

### 8.4 API Constraints

| Constraint | Value |
|---|---|
| Max request body size | Configurable server setting; default 500 MB total. |
| Request timeout | Configurable; default 300 seconds. |
| Concurrent requests | Each request gets an isolated workspace — no shared state. |
| Authentication | None in v1 (add API key / OAuth in post-v1 if needed). |

### 8.5 Example Requests (curl)

All examples use **`sampleConfig.json`**.

**Blueprint 1 only — direct mapping, 1 source → 1 target:**

Submit a config containing only `bp_direct_one_source_one_target`, or the full sample (ZIP response when 2 blueprints).

```bash
curl -X POST http://localhost:8000/api/v1/transform \
  -F "config=@sampleConfig.json;type=application/json" \
  -F "files=@employees.csv" \
  -F "files=@departments.csv" \
  -o direct_mapping_outputs.zip
```

**Full sample config — both blueprints (2 targets, direct mapping only):**

| Blueprint | Sources | Output |
|---|---|---|
| `bp_direct_one_source_one_target` | `employees.csv` | `employees_export.csv` |
| `bp_direct_two_sources_one_target` | `employees.csv` + `departments.csv` | `employees_with_department.csv` |

Upload `employees.csv` and `departments.csv`. Response: ZIP with both target files.

### 8.6 Running the API Server

```bash
uvicorn csv_data_transformer.api.app:app --host 0.0.0.0 --port 8000 --reload
```

| Environment variable | Default | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Bind host |
| `API_PORT` | `8000` | Bind port |
| `API_MAX_BODY_MB` | `500` | Max multipart request size |
| `API_TIMEOUT_SEC` | `300` | Request processing timeout |
| `LOG_LEVEL` | `INFO` | Application log level |

### 8.7 API Module Structure

The API layer is a thin HTTP shell over the pipeline orchestrator. **No transform logic in route handlers.**

```
api/
├── app.py                  # create_app() — FastAPI instance, lifespan, CORS, routers
├── dependencies.py         # get_settings(), inject orchestrator/workspace
├── middleware.py           # RequestIdMiddleware, process-time header
├── exception_handlers.py   # register_exception_handlers(app)
├── schemas/                # OpenAPI-documented Pydantic DTOs (not pipeline config models)
│   ├── errors.py
│   ├── health.py
│   └── validate.py
├── routes/
│   ├── health.py           # Router: tags=["Health"]
│   └── transform.py        # Router: tags=["Transform"]
├── workspace.py            # WorkspaceManager — create/cleanup temp dirs
└── responses.py            # build_csv_response(), build_zip_response()
```

**Layer responsibilities:**

| Module | Responsibility |
|---|---|
| `routes/*.py` | Parse HTTP input, call orchestrator, return HTTP response |
| `schemas/*.py` | Request/response shapes for Swagger — separate from `config/models.py` |
| `exception_handlers.py` | Map `TransformerError` subclasses → `ErrorResponse` + status code |
| `workspace.py` | Isolate per-request file I/O; always cleanup in `finally` |
| `responses.py` | Set `Content-Type`, `Content-Disposition`, `X-*` headers |
| `app.py` | Wire everything; define OpenAPI metadata |

**Router prefix:** All v1 routes mounted under `/api/v1` via `APIRouter(prefix="/api/v1")`.

### 8.8 Swagger / OpenAPI Setup

FastAPI generates OpenAPI 3.1 documentation automatically. Configure explicitly in `api/app.py`:

#### 8.8.1 Documentation URLs

| URL | Purpose |
|---|---|
| `/api/v1/docs` | **Swagger UI** — interactive API explorer (primary) |
| `/api/v1/redoc` | ReDoc — alternative read-only docs |
| `/api/v1/openapi.json` | Raw OpenAPI 3.1 schema (for codegen / Postman import) |

#### 8.8.2 Application Metadata

```python
app = FastAPI(
    title="CSV Data Transformer API",
    description="Upload a JSON config and source CSV files; receive transformed CSV output.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=[
        {"name": "Health", "description": "Liveness and readiness checks"},
        {"name": "Transform", "description": "CSV transform and validation operations"},
    ],
)
```

#### 8.8.3 Pydantic Response Schemas (for OpenAPI)

Define in `api/schemas/` — used as `response_model` on JSON endpoints:

**`HealthResponse`**

```python
class HealthResponse(BaseModel):
    status: Literal["ok"]
```

**`ValidateResponse`**

```python
class ValidateResponse(BaseModel):
    valid: bool
    migration_id: str
    blueprint_count: int
    output_files: list[str]
    required_files: list[str]
    uploaded_files: list[str]
```

**`ErrorResponse`**

```python
class ErrorDetail(BaseModel):
    field: str | None = None
    message: str

class ErrorResponse(BaseModel):
    error: str           # e.g. "validation_failed", "transform_failed"
    message: str
    gate: str | None = None
    blueprint_id: str | None = None
    details: list[ErrorDetail] = []
```

#### 8.8.4 Documenting Multipart Endpoints

`POST /transform` and `POST /validate` use `multipart/form-data`. Document with FastAPI `File` / `UploadFile` and explicit `responses` for file and error outputs:

```python
@router.post(
    "/transform",
    tags=["Transform"],
    summary="Transform CSV files",
    description="Upload config JSON and source CSV files. Returns one CSV or a ZIP of outputs.",
    responses={
        200: {
            "description": "Transformed CSV file or ZIP archive",
            "content": {
                "text/csv": {},
                "application/zip": {},
            },
        },
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def transform(
    config: UploadFile = File(..., description="JSON config file (see sampleConfig.json)"),
    files: list[UploadFile] = File(..., description="Source CSV files referenced in config"),
) -> Response: ...
```

#### 8.8.5 OpenAPI Conventions

| Convention | Rule |
|---|---|
| Tags | `Health` for health routes; `Transform` for transform/validate |
| `operation_id` | Explicit snake_case IDs: `transform_csv`, `validate_config`, `health_check` |
| `summary` | Short one-line label shown in Swagger UI |
| `description` | Markdown-supported longer explanation per endpoint |
| JSON endpoints | Always set `response_model=` for auto-schema generation |
| File endpoints | Use `responses={}` dict for `text/csv` and `application/zip` content types |
| Error endpoints | Reference `ErrorResponse` model on all 4xx/5xx responses |
| Deprecation | Use `deprecated=True` on route decorator when sunsetting |

#### 8.8.6 Exception Handler Registration

Register in `api/exception_handlers.py` and call from `create_app()`:

```python
@app.exception_handler(ConfigValidationError)
async def config_validation_handler(request, exc: ConfigValidationError):
    return JSONResponse(status_code=400, content=ErrorResponse(...).model_dump())

@app.exception_handler(TransformError)
async def transform_handler(request, exc: TransformError):
    return JSONResponse(status_code=422, content=ErrorResponse(...).model_dump())
```

Unmapped exceptions fall through to a generic `500` handler that logs the traceback server-side and returns a safe `ErrorResponse`.

#### 8.8.7 CORS (v1)

Enable permissive CORS for local development and Swagger UI testing:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Restrict in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

#### 8.8.8 Swagger UI Verification Checklist

- [ ] `/api/v1/docs` loads without errors
- [ ] All three endpoints visible under correct tags
- [ ] `POST /transform` shows `config` (file) and `files` (file array) inputs
- [ ] `POST /validate` shows `response_model: ValidateResponse` schema
- [ ] Error responses show `ErrorResponse` schema with example values
- [ ] `GET /health` shows `HealthResponse` schema
- [ ] OpenAPI JSON importable into Postman / Insomnia

---

## 9. CLI Interface (Secondary — Dev / Local)

```
python -m csv_data_transformer run --config ./sampleConfig.json [--dry-run] [--log-level INFO]
python -m csv_data_transformer validate --config ./sampleConfig.json
```

| Command | Description |
|---|---|
| `run` | Execute all blueprints against local filesystem paths. |
| `validate` | Run G0 + G1 pre-flight checks only. |

| Flag | Description |
|---|---|
| `--config` | Path to JSON configuration file (required). |
| `--dry-run` | Execute transforms but skip target writes (G4 still runs). |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`. |

---

## 10. Technology Stack

| Component | Choice |
|---|---|
| Language | Python 3.11+ |
| API framework | FastAPI |
| ASGI server | Uvicorn |
| Data engine | Pandas |
| Numerics | NumPy |
| Config models | Pydantic v2 |
| Config validation | `jsonschema` + Pydantic against bundled schema |
| Testing | `pytest`, `httpx` (API tests) |
| Packaging | `pyproject.toml` |

---

## 11. Testing Requirements

| Level | Scope |
|---|---|
| Unit | Factories, column-name translation, operator dispatch, CASE/REGEXP_REPLACE compilation, cast logic, validator rules. |
| Integration | End-to-end blueprint runs against fixture CSVs in `tests/fixtures/`. |
| API | `httpx` tests for `/transform`, `/validate`, `/health` — single output, multi-output ZIP, single-file and multi-file join paths. |
| Regression | Both sample blueprints from `sampleConfig.json` produce expected output snapshots. |
| Pre-flight | Missing file uploads, file-size-limit, and validation error responses. |

---

## 12. Future Enhancements (Post-v1)

| Enhancement | Benefit |
|---|---|
| XLSX reader/writer via `file_options.format` | Exercises factory OCP; already reserved in connection model. |
| Parquet support | Faster I/O for larger datasets. |
| YAML config reader | Alternative config format. |
| Validation summary report (JSON) | Audit artifact per migration run. |
| Config linter enhancements | Deeper expression syntax checks without data. |
| API authentication (API key / OAuth) | Secure production deployment. |
| Async job endpoint | Long-running transforms with polling/webhook. |

---

## 13. Implementation Tracking Steps

Mark each step `[x]` when complete.

### Phase 0 — Project Setup

- [x] **0.1** Initialize Python project (`pyproject.toml`, package name `csv_data_transformer`, Python 3.11+).
- [x] **0.2** Add dependencies: `pandas`, `numpy`, `pydantic`, `jsonschema`, `fastapi`, `uvicorn`, `python-multipart`, `pytest`, `httpx`.
- [x] **0.3** Create module skeleton per §3.4.
- [x] **0.4** Configure structured logging (`audit/logger.py`).
- [x] **0.5** Define domain exceptions (`exceptions.py`).
- [x] **0.6** Add fixture CSVs under `data/input/` and ensure `data/output/` is empty.

### Phase 1 — Configuration Layer

- [x] **1.1** Define Pydantic models for all config blocks (§2).
- [x] **1.2** Implement `ConfigReader` ABC and `JsonConfigReader`.
- [x] **1.3** Implement `ConfigReaderFactory`.
- [x] **1.4** Author JSON Schema (`schema/config.schema.json`).
- [x] **1.5** Implement G0 validator — schema, aliases, operators, mappings.
- [x] **1.6** Unit tests: valid/invalid config cases with actionable error messages.

### Phase 2 — I/O Layer

- [x] **2.1** Implement `LOCAL_FILE_DIRECTORY` connection resolver with per-connection `file_options`.
- [x] **2.2** Implement `DataReader` ABC and `CsvDataReader` with encoding/delimiter/quote options.
- [x] **2.3** Implement source file-size guard (`max_file_size_mb`) — abort before read.
- [x] **2.4** Implement `DataReaderFactory` (format → reader).
- [x] **2.5** Implement `DataTargetWriter` ABC and `CsvDataWriter`.
- [x] **2.6** Implement target-empty guard (G1/G4) — abort if target has content.
- [x] **2.7** Implement atomic write (temp → rename).
- [x] **2.8** Implement `DataTargetFactory`.
- [x] **2.9** Unit tests: read options, size limit rejection, empty-target enforcement, atomic write.

### Phase 3 — Column Names & Operators

- [x] **3.1** Implement `column_names.py` — dot ↔ double-underscore translation.
- [x] **3.2** Implement `operators.py` — full operator dispatch (§2.5).
- [x] **3.3** Implement predicate and group evaluation for filters and join conditions.
- [x] **3.4** Unit tests: all operators, nested AND/OR groups, alias translation edge cases.

### Phase 4 — Execution Engine

- [x] **4.1** Implement `ExecutionEngine` ABC and `PandasExecutionEngine`.
- [x] **4.2** Implement pre-filter and post-filter (predicate, group, expression forms).
- [x] **4.3** Implement sequential joins (LEFT, INNER, RIGHT, OUTER) with condition parsing.
- [x] **4.4** Implement derivations: `EXPRESSION`, `REGEXP_REPLACE`, `CASE`.
- [x] **4.5** Implement mapping builder (`DIRECT`, `DERIVED`, `EXPRESSION`) with `default_value`.
- [x] **4.6** Implement dtype casting with fail-first on coercion failure.
- [x] **4.7** Unit tests: each engine operation in isolation.

### Phase 5 — Pipeline Orchestration

- [ ] **5.1** Implement G1 pre-flight checks in `pipeline/validator.py`.
- [ ] **5.2** Implement `BlueprintRunner` — full step order (§4.1).
- [ ] **5.3** Implement checkpoint logging at every gate.
- [ ] **5.4** Implement G4 nullable verification before write.
- [ ] **5.5** Implement `Orchestrator` — sequence blueprints, fail-first on any error.
- [ ] **5.6** Integration test: single-file transform (use case A) end-to-end.
- [ ] **5.7** Integration test: single-source split into multiple targets (use case D).
- [ ] **5.8** Integration test: multi-blueprint multi-output different sources (use case C).
- [ ] **5.9** Integration test: multi-file join single-output (use case B) end-to-end.

### Phase 6 — REST API & Swagger

- [ ] **6.1** Implement ephemeral workspace manager (`api/workspace.py`).
- [ ] **6.2** Implement Pydantic API schemas (`api/schemas/`) — `HealthResponse`, `ValidateResponse`, `ErrorResponse`.
- [ ] **6.3** Implement `create_app()` in `api/app.py` with OpenAPI metadata, CORS, router mounting.
- [ ] **6.4** Implement route modules: `routes/health.py`, `routes/transform.py` with tags, summaries, `response_model`.
- [ ] **6.5** Implement `exception_handlers.py` — domain errors → `ErrorResponse` JSON.
- [ ] **6.6** Implement multipart upload handling — map uploaded filenames to config `file_name` refs.
- [ ] **6.7** Implement response builders — single CSV (1 blueprint) or ZIP (2+ blueprints).
- [ ] **6.8** Verify Swagger UI at `/api/v1/docs` — all endpoints, schemas, and error models visible.
- [ ] **6.9** API integration tests with `httpx` — direct mapping paths + error response shape.
- [ ] **6.10** Wire orchestrator to accept injected workspace paths (API mode vs. CLI mode).

### Phase 7 — CLI, Docs & Release

- [ ] **7.1** Implement `python -m csv_data_transformer run` and `validate` commands.
- [ ] **7.2** Implement `--dry-run` and `--log-level` flags.
- [ ] **7.3** Add `README.md` with API usage, **Swagger URL** (`/api/v1/docs`), curl examples, config walkthrough.
- [ ] **7.4** Full end-to-end test — API and CLI paths with `sampleConfig.json`.
- [ ] **7.5** SOLID review — confirm XLSX addition needs no orchestrator edits.
- [ ] **7.6** Tag v1.0.0 release.

---

## Appendix A — `sampleConfig.json` Reference

The single sample config documents **direct mapping only** — no filters, derivations, or expressions.

### Blueprint 1: `bp_direct_one_source_one_target`

| Aspect | Value |
|---|---|
| Pattern | **1 source → 1 target** |
| Source | `employees.csv` (alias `emp`) |
| Joins | None (`joins: []`) |
| Transforms | None — all mappings `source_type: DIRECT` |
| Target | `employees_export.csv` |
| Upload | `employees.csv` |

### Blueprint 2: `bp_direct_two_sources_one_target`

| Aspect | Value |
|---|---|
| Pattern | **2 sources → 1 target** |
| Root | `employees.csv` (alias `emp`) |
| Join | LEFT `departments.csv` (`dept`) on `emp.department_id = dept.id` |
| Transforms | None — all mappings `source_type: DIRECT` |
| Target | `employees_with_department.csv` |
| Upload | `employees.csv` + `departments.csv` |

### Minimal direct-mapping checklist

```
✓ pre_filters: []
✓ derivations: []
✓ post_filters: []
✓ mappings[].source_type: "DIRECT"
✓ mappings[].source_value: "{alias}.{column}"
✓ cast_to + is_nullable on each mapping
```

Advanced patterns (filters, derivations, expressions, source split) use the same blueprint structure — add sections as needed.

---

## Appendix B — Glossary

| Term | Definition |
|---|---|
| Blueprint | A single ETL pipeline: one or more sources → exactly one target CSV. |
| Direct mapping | Column copied from source to target via `source_type: DIRECT` with optional rename and cast. No filters or derivations. |
| Output set | All target CSVs produced by the blueprints in one config/run. |
| Connection | Named storage location with format-specific `file_options`. |
| Fail-first | Abort the entire run on the first validation or transformation error. |
| Derivation | Sequential intermediate column in the `deriv` namespace. |
| Physical column name | Internal name `{alias}__{column}` used in the working DataFrame. |
| Working DataFrame | In-memory DataFrame after joins and derivations, before target mapping. |
| Workspace | Ephemeral temp directory created per API request for input/output files. |
| Source split | Pattern where multiple blueprints read the same source file and produce different target CSVs (use case D). |
