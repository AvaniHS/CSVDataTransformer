# Core AI Instruction Set: Config UI — Architecture, UX, FE, BE & Quality

You are an expert full-stack engineer and product-minded UI designer. Your task is to build **config_ui** — a wizard-style web app for authoring valid CSV Data Transformer config JSON. You must strictly adhere to the following principles for all generated code, layouts, styling, and API design.

**Authoritative references:**

| Document | Purpose |
|---|---|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | Product spec, wizard flow, UX principles §3.4 |
| [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) | Parent engine use cases A–D, G0 gates |
| [`../schema/config.schema.json`](../schema/config.schema.json) | Output JSON Schema |
| [`../docs/CONFIG_TEMPLATE.md`](../docs/CONFIG_TEMPLATE.md) | Config field reference |
| [`../docs/codeSanityGuilinesForAI.md`](../docs/codeSanityGuilinesForAI.md) | Parent engine rules (error shape, G0, API patterns) |

**Hard boundary:** The frontend must **never** import or depend on `csv_data_transformer`. Config authoring logic that belongs on the server lives in **config_ui/backend/** only.

---

## 1. Code Organization & Modularity

### 1.1 Repository layout (mandatory)

```
config_ui/
├── REQUIREMENTS.md
├── codeSanityGuilinesForAI.md
├── requirements.txt          # BE Python deps
├── backend/
│   ├── app.py                # create_app() only
│   ├── exceptions.py
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── exception_handlers.py
│   │   ├── middleware.py
│   │   ├── routes/
│   │   └── schemas/          # OpenAPI DTOs — NOT exported config.json shape docs
│   ├── domain/               # Session, blueprint builder, config assembler
│   ├── validation/           # G0, upload rules, header-only target check
│   └── storage/              # Session workspace, uploaded files
└── frontend/
    ├── package.json
    └── src/
        ├── api/              # Typed REST client
        ├── components/       # Shared, reusable UI primitives
        ├── features/         # One folder per wizard step
        ├── hooks/              # Shared React hooks
        ├── layouts/            # Shell, stepper, settings drawer
        ├── styles/             # Design tokens, global CSS
        ├── types/              # FE domain types (wizard state)
        └── App.tsx
```

* **Monolithic files are prohibited** — no single 800-line `Wizard.tsx` or `routes.py`.
* **Feature folders** map to wizard steps (`setup`, `upload`, `pre-filters`, `joins`, `derivations`, `post-filters`, `mappings`, `review`).
* **Loose coupling:** FE talks to BE only via REST. BE does not serve transform/pandas logic to the browser.

### 1.2 Responsibility split

| Layer | Owns | Must NOT own |
|---|---|---|
| **FE** | Wizard UX, client-side CSV preview parsing, form state, step navigation, download trigger | G0 validation rules, final config JSON assembly, file persistence semantics |
| **BE** | Session lifecycle, upload storage, schema inference, config generation, G0 validation, import/export | React components, CSS, browser-only APIs |
| **Shared contract** | OpenAPI schema, error JSON shape, `schema/config.schema.json` | — |

### 1.3 Small building blocks

* Wizard steps compose shared components (`ColumnPicker`, `FilterBuilder`, `SchemaTable`, `ValidationBanner`).
* Complex config assembly is orchestrated in `domain/` — route handlers stay thin.
* Adding a new derivation type or filter operator extends one registry + one form component — not a rewrite of the wizard.

---

## 2. UX & Visual Design (mandatory)

Follow [`REQUIREMENTS.md` §3.4](REQUIREMENTS.md). Engagement comes from **clarity and progress**, not visual noise.

### 2.1 Tone & layout

| Rule | Requirement |
|---|---|
| **Professional tool** | Structured shell: header, left stepper, main panel, optional context sidebar (“Available columns”). |
| **Not plain** | Use spacing, section cards, labels, helper text — never ship unstyled default form dumps. |
| **Not loud** | No full-screen gradients, neon accents, glassmorphism stacks, parallax, or decorative motion. |
| **Step orientation** | Always show current step name, index (e.g. “Step 3 of 8”), and Back / Continue. |
| **Settings access** | `migration_id`, `client_id`, paths editable from persistent settings bar/drawer on every step. |

### 2.2 Engagement patterns (required)

* **Progress:** completed steps show checkmarks; current step is highlighted with the single accent color.
* **Context panel:** during filters, joins, derivations, and mappings, show `alias.column` and `deriv.*` names the user can reference.
* **Inline validation:** field-level errors under inputs; step-level summary at top when Continue is blocked.
* **Feedback:** toast or banner on upload success/failure, validate pass/fail, export complete.
* **Schema preview:** tabular header + sample rows after source upload; header-only confirmation for targets.

### 2.3 Design tokens (v1)

Define once in `frontend/src/styles/tokens.css` (or equivalent) and reuse everywhere:

| Token | Guideline |
|---|---|
| Background | Light neutral (`#f5f6f8` or similar) |
| Surface | White cards with subtle border or shadow |
| Accent | **One** restrained color for primary button + active step |
| Semantic | Green / amber / red **only** for success / warning / error |
| Typography | One sans-serif stack; monospace **only** for JSON preview |
| Density | Comfortable — ~40–48px control height, 16–24px section gaps |

**v1:** single light theme only. No dark-mode toggle unless explicitly requested.

### 2.4 Accessibility

* WCAG-friendly contrast on text and controls.
* Visible `:focus-visible` rings — do not remove outlines without a replacement.
* Icon-only buttons need `aria-label`.
* Step changes should move focus to the step heading or first field.
* Do not rely on color alone for error state — use text + icon.

### 2.5 UX anti-patterns (prohibited)

* Marketing-style hero blocks inside wizard steps.
* Auto-advancing steps without user confirmation.
* Hiding validation errors only in the browser console.
* Free-text column names where dropdowns are required (joins, mappings) — see §6.
* Blocking the whole UI with a spinner during minor field edits.

---

## 3. Frontend Rules (React + Vite)

### 3.1 Stack & conventions

* **React 18+** with **TypeScript** (strict mode).
* **Vite** for dev/build.
* Prefer **function components** and hooks; no class components.
* Prefer a lightweight router only if needed — wizard can use step index in state for v1.
* State: colocate step state; lift shared wizard state to a context or store (`WizardProvider`) — avoid prop drilling across 8 steps.

### 3.2 Component rules

| Rule | Requirement |
|---|---|
| **SRP** | One component, one job. Split “form + table + actions” into composable pieces. |
| **Presentational vs container** | Dumb UI in `components/`; step orchestration in `features/*/`. |
| **No business logic in JSX** | Extract predicates, column lists, and validators to pure functions or hooks. |
| **Controlled inputs** | Form fields are controlled; debounce only API calls, not visual input. |
| **Loading / empty / error** | Every async view has all three states — no blank panels. |

### 3.3 API client

* Centralize HTTP in `src/api/client.ts` + per-resource modules (`session.ts`, `config.ts`).
* Use types aligned with BE OpenAPI (hand-written or generated — stay in sync).
* Send `session_id` on all session-scoped calls.
* Map API errors to user-facing messages; attach `details` to the relevant step/field when BE provides path hints.
* No `fetch` scattered across feature files.

### 3.4 Client-side CSV handling

* Parse uploads in the browser **only** for preview and type inference hints.
* **Target files:** reject data rows client-side first (fast feedback), then let BE enforce the same rule.
* Do not persist full CSV data in `localStorage` — session files live on BE.
* Infer `cast_to` suggestions from sample values; user override always wins.

### 3.5 FE coding anti-patterns (prohibited)

* Importing Python, pandas, or parent engine packages.
* Duplicating G0 rules in FE as the source of truth (FE may do lightweight UX checks only).
* `any` types on wizard state or API responses without justification.
* Inline styles for every element — use tokens + shared classes/modules.
* `useEffect` chains that are hard to reason about — prefer explicit event handlers or reducers for wizard navigation.

---

## 4. Backend Rules (FastAPI)

### 4.1 Module layout

Mirror parent engine API discipline ([`../docs/codeSanityGuilinesForAI.md` §7](../docs/codeSanityGuilinesForAI.md)):

* `app.py` — `create_app()` only.
* `api/routes/` — thin handlers.
* `api/schemas/` — request/response DTOs for OpenAPI.
* `domain/` — session model, blueprint builder, `config.json` assembler.
* `validation/` — G0 (jsonschema + semantic rules), upload validation.
* `storage/` — session directories, safe paths, cleanup.

### 4.2 Dependency boundaries

| Rule | Requirement |
|---|---|
| **No pandas in routes** | Routes parse HTTP, call services, return DTOs. |
| **Optional parent package** | BE may `pip install -e` parent for shared G0 validator — but FE never does. |
| **Schema is law** | Generated JSON must validate against `schema/config.schema.json`. |
| **Engine order** | Emit pipeline arrays in engine order: mappings before `post_filters` in JSON even though wizard UX order is derive → post-filter → map. |

### 4.3 Session & file handling

* One **isolated workspace directory** per session under a configurable base path.
* Validate filenames — no path traversal (`..`, absolute paths).
* Enforce **header-only** target CSVs server-side (reject any data row).
* Enforce source count = N, target count = M before generate.
* Delete session workspace in `finally` on session delete/TTL; document retention policy.
* Default `base_path` / `target_path` in generated config to session upload directory when user leaves paths blank.

### 4.4 Config import / export

* **Import:** parse JSON → G0 → hydrate session model → return wizard-shaped DTO for FE.
* **Export / generate:** assemble from session → G0 → return JSON.
* Round-trip must be lossless for all UI-supported features ([`REQUIREMENTS.md` §5](REQUIREMENTS.md)).

---

## 5. Error Handling (Fail-First, User-Visible)

Config UI uses the same **fail-first** philosophy as the engine: invalid uploads, schema violations, and assembly errors **stop** the operation and return a clear message. No silent fixes.

### 5.1 Validation layers

| Layer | When | Examples |
|---|---|---|
| **Client UX** | Before Continue / upload | Missing file, target has data rows, empty required metadata |
| **BE upload** | On `POST .../sources` / `targets` | Wrong MIME, empty file, header-only violation |
| **G0** | On validate / generate / import | Schema, duplicate aliases, bad operator, broken column refs |
| **Assembly** | On generate | Blueprint missing root, join without conditions |

Abort at the first failing layer; do not return partial `config.json` marked valid.

### 5.2 Domain exceptions

Define in `backend/exceptions.py`:

```python
class ConfigUIError(Exception):
    """Base error for config UI domain failures."""

class SessionError(ConfigUIError):
    session_id: str

class UploadValidationError(ConfigUIError):
    session_id: str
    file_role: str  # "source" | "target"

class ConfigBuildError(ConfigUIError):
    blueprint_id: str | None

class G0ValidationError(ConfigUIError):
    details: list[dict]  # jsonschema or semantic errors
```

* Never raise bare `Exception` from business logic.
* Wrap I/O errors: `raise UploadValidationError(...) from exc`.
* Never swallow errors (`except: pass`).

### 5.3 API error responses

Align with parent engine shape for consistency:

```json
{
  "error": "validation_failed",
  "message": "Human-readable description",
  "gate": "G0",
  "blueprint_id": "bp_employees_export",
  "details": [
    { "path": "blueprints[0].mappings[2].source_column", "message": "Unknown alias" }
  ]
}
```

| HTTP status | When |
|---|---|
| `400` | Bad request body, wrong file count, invalid session id |
| `404` | Session not found |
| `413` | Upload too large |
| `422` | G0 failure, upload rule violation, config build failure |
| `500` | Unexpected error — log traceback server-side only |

FE must surface `message` and map `details` to fields/steps when `path` is present.

### 5.4 Wizard-step error routing

When G0 or build fails, BE should prefer `details` entries that FE can route:

| Config area | Wizard step |
|---|---|
| `migration_id`, paths, blueprint count | Setup |
| `connections`, file refs | Upload |
| `pre_filters`, `joins[].pre_filters` | Pre-filters |
| `sources.joins` | Joins |
| `derivations` | Derivations |
| `post_filters` | Post-filters |
| `mappings` | Map to target |

---

## 6. Dropdown-First Config Authoring

Per [`REQUIREMENTS.md`](REQUIREMENTS.md), users pick columns and operators from lists — not free typing — wherever the engine expects qualified names.

| Area | UI rule |
|---|---|
| Join conditions | Column dropdowns per alias; operator dropdown |
| Pre-filters | Column dropdown + operator; expression mode is advanced escape hatch |
| Mappings DIRECT | `alias.column` dropdown |
| Mappings DERIVED | `deriv.name` dropdown |
| `cast_to` | Fixed enum dropdown |
| `join_type` | Fixed enum dropdown |

**Advanced expression** fields (derivations, EXPRESSION mappings) are allowed with helper text linking to engine expression rules. Validate on blur via BE where possible.

---

## 7. Logging & Traceability

### 7.1 Backend logging

* Configure once; use stdlib `logging` — no `print()` in production paths.
* Format (match parent):

```
[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s
```

* One logger per module: `logger = logging.getLogger(__name__)`.

| Level | Use for |
|---|---|
| `INFO` | Session created, file uploaded, config generated, G0 pass |
| `WARNING` | Recoverable session TTL expiry |
| `ERROR` | Validation failure — log concise context **before** raising |
| `DEBUG` | Workspace paths, assembly steps |

Include `session_id`, `migration_id`, and `blueprint_id` in messages when available. Do not log full CSV contents.

### 7.2 Request tracing

* Add `X-Request-Id` via middleware (same pattern as parent API).
* Return it on responses for support correlation.

### 7.3 Frontend diagnostics

* No `console.log` left in committed code — use a dev-only debug flag if needed.
* Network errors: show actionable message (“Cannot reach server — is the API running on port 8002?”).

---

## 8. API Structure & Swagger Conventions

Prefix: `/api/v1/`. Default dev URL: `http://localhost:8002` (avoid clash with transform API on **8001**).

### 8.1 Draft endpoints (implement per [`REQUIREMENTS.md` §9](REQUIREMENTS.md))

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/session` | Create session |
| `POST` | `/session/{id}/sources` | Upload source CSV |
| `POST` | `/session/{id}/targets` | Upload target CSV (headers only) |
| `GET` | `/session/{id}` | Wizard state |
| `PUT` | `/session/{id}/metadata` | Metadata + paths |
| `PUT` | `/session/{id}/blueprints/{bp}` | Blueprint slice updates |
| `POST` | `/config/validate` | G0 validate JSON body |
| `POST` | `/config/generate` | Build JSON from session |
| `POST` | `/config/import` | Load existing JSON into session |
| `GET` | `/config/export` | Download generated JSON |

### 8.2 OpenAPI requirements

* Every JSON endpoint declares `response_model`.
* Every endpoint has `tags`, `summary`, and `operation_id`.
* File upload endpoints document multipart schema and error responses.
* Register exception handlers — never leak stack traces.
* Docs URLs must work:

| URL | Purpose |
|---|---|
| `http://localhost:8002/api/v1/docs` | Swagger UI |
| `http://localhost:8002/api/v1/redoc` | ReDoc |
| `http://localhost:8002/api/v1/openapi.json` | OpenAPI schema |

### 8.3 CORS

* Enable CORS for Vite dev origin (`http://localhost:5173`) in development.
* Tighten origins in production via config — no `*` in production.

---

## 9. Testing Expectations

### 9.1 Backend

* Unit: G0 failures raise `G0ValidationError` with structured `details`.
* Unit: target CSV with data rows rejected at upload.
* Unit: config generator emits mappings before `post_filters` in JSON.
* Unit: join `pre_filters` use join alias only.
* Integration: full session → generate → validate passes for use cases A–D fixtures.
* API: assert error JSON shape and HTTP status codes.

### 9.2 Frontend

* Component tests for shared builders (`FilterBuilder`, `ColumnPicker`) with React Testing Library.
* Step tests: Continue disabled when required fields missing.
* Contract test (optional v1): mock API or use MSW against OpenAPI examples.
* Do not snapshot-test entire pages — test behavior and accessibility roles.

### 9.3 UX acceptance (manual or e2e)

* Stepper visible on all steps after setup.
* Available-columns panel visible on filter/join/derive/map steps.
* Validation errors visible without opening devtools.
* Visual design matches §2 — structured, restrained, not default-browser-plain.

---

## 10. Performance & Safety

* Enforce max upload size on BE before writing to disk.
* Sanitize session ids and blueprint ids in paths.
* Do not execute user expressions with Python `eval()` on the server — generation only serializes configured strings; engine evaluates at transform time.
* JSON preview on review step: virtualize or truncate very large configs — warn if > N KB.
* Session TTL and cleanup job/documented cron for orphaned workspaces.

---

## 11. Structural Patterns (SOLID Summary)

| Principle | Config UI application |
|---|---|
| **SRP** | Step components render; services validate; routes transport HTTP. |
| **OCP** | New operators/derivation types extend registries, not switch statements across the app. |
| **LSP** | Shared “rule builder” interfaces for pre-filter and post-filter UIs where shapes overlap. |
| **ISP** | Split API client types per resource — FE does not import monolithic `api.ts` god-object. |
| **DIP** | FE depends on API contract; BE depends on `domain` protocols, not FastAPI request objects inside builders. |

**Type hints:** All public Python functions and exported TypeScript types must be explicit.

---

## 12. What NOT to Do (checklist)

* Do not import `csv_data_transformer` in the frontend.
* Do not run pandas transforms in config UI v1.
* Do not ship a plain unstyled wizard “for now”.
* Do not add flashy gradients, animation libraries for decoration, or unrelated dashboard widgets.
* Do not allow free-text column names in joins or DIRECT mappings.
* Do not accept target CSVs with data rows.
* Do not return success when G0 failed.
* Do not store uploaded files only in browser memory without BE session backing.
* Do not duplicate conflicting validation rules — BE is the source of truth for G0.
* Do not hardcode transform API port 8001 into config UI without documenting both services.

---

## 13. References

| Resource | Link |
|---|---|
| Config UI requirements | [`REQUIREMENTS.md`](REQUIREMENTS.md) |
| Parent engine AI guidelines | [`../docs/codeSanityGuilinesForAI.md`](../docs/codeSanityGuilinesForAI.md) |
| JSON Schema | [`../schema/config.schema.json`](../schema/config.schema.json) |
| Config template guide | [`../docs/CONFIG_TEMPLATE.md`](../docs/CONFIG_TEMPLATE.md) |
| Sample configs | [`../sampleConfig.json`](../sampleConfig.json), [`../samples/manual_advanced/`](../samples/manual_advanced/README.md) |
