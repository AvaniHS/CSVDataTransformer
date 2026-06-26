# Config UI — Requirements

| Field | Value |
|---|---|
| Version | 0.1 |
| Status | **v1 implemented** — see [`README.md`](README.md) for run instructions |
| Parent engine | [`docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) v1.6 |

## 1. Purpose

A **wizard-style web UI** that lets users build valid CSV Data Transformer config JSON files by uploading source CSVs and empty target CSVs (headers only), configuring transforms through dropdowns and guided forms, then **previewing, validating, and downloading** the config.

Generated output must conform to [`schema/config.schema.json`](../schema/config.schema.json) and pass **G0** validation.

**v1 scope:** config authoring only. Running transforms from this UI is a **later stage**; architecture must still allow the FE to call the existing transform API when that is added.

---

## 2. Alignment with engine use cases (§1.1)

The UI must support **all** primary engine scenarios:

| Use case | UI meaning | Blueprints |
|---|---|---|
| **A** — Single-file transform | 1 source, 1 target | 1 |
| **B** — Multi-file join | 2+ sources joined, 1 target | 1 |
| **C** — Multiple outputs (different sources) | Each blueprint may use a **different source set** | 2+ (one per target) |
| **D** — Single source split | **Same root CSV** across blueprints; different filters / derivations / mappings per target | 2+ (one per target) |

**Multiple targets** always means **multiple blueprints** (one target CSV per blueprint), matching engine use cases **C** and **D** (and A/B when M=1).

Users choose:

- **Number of source files** (N)
- **Number of target files** (M) → M blueprints

Each target file is an **empty CSV with headers only** — headers define output column names.

---

## 3. Architecture

### 3.1 Loose coupling (required)

| Layer | Responsibility |
|---|---|
| **Frontend (FE)** | Wizard UX, CSV upload/parsing in browser, calls REST API, preview/download |
| **Backend (BE)** | Config CRUD, schema validation (G0), JSON generation, optional future proxy to transform API |

FE must not embed engine/pandas logic. All validation and JSON assembly exposed via **BE APIs**.

### 3.2 v1 vs later

| Phase | FE | BE |
|---|---|---|
| **v1** | Full wizard; preview/download config | Validate + build/export `config.json`; load/edit existing config |
| **Later** | “Run transform” button | Proxy to `csv_data_transformer` `/api/v1/transform` |

### 3.3 Recommended stack

| Layer | Recommendation | Rationale |
|---|---|---|
| BE | **FastAPI** (separate app under `config_ui/backend/`) | Matches parent API patterns; OpenAPI for FE |
| FE | **React + Vite** (under `config_ui/frontend/`) | Multi-step wizard, rich dropdowns, loose coupling |
| Shared validation | `jsonschema` + reuse parent `schema/config.schema.json` | Same G0 rules as engine |

### 3.4 Visual design & UX principles

The UI should feel like a **focused professional tool** — not a bare form, and not a flashy marketing site.

| Principle | Guideline |
|---|---|
| **Tone** | Calm, confident, workmanlike. Suitable for repeated use by data/ops users. |
| **Not plain** | Use clear hierarchy, spacing, section cards, and a visible stepper so the wizard feels intentional — avoid an unstyled “default HTML form” look. |
| **Not loud** | No heavy gradients, neon accents, parallax, or decorative animation. Avoid illustration-heavy empty states. |
| **Engagement** | Keep users oriented and progressing: step progress, inline validation, “available columns” context panel, success/error toasts, completed-step checkmarks, short helper text per section. |
| **Color** | Neutral background (light grey or soft white) + **one** restrained accent for primary actions and active step. Semantic colors only for success / warning / error. |
| **Typography** | One clean sans-serif stack; clear heading vs body vs label sizes; monospace for JSON preview only. |
| **Density** | Comfortable form density — enough whitespace to scan, not cramped; avoid oversized marketing-style hero blocks. |
| **Components** | Consistent buttons, inputs, tables for schema preview, collapsible sections for filters/derivations. Subtle borders/shadows — no skeuomorphism. |
| **Feedback** | Every save/validate/upload shows clear outcome. G0 errors map to the wizard step and field where possible. |
| **Accessibility** | Sufficient contrast, keyboard-friendly controls, visible focus states — engagement without relying on color alone. |

**Engagement comes from clarity and progress**, not from visual noise.

**Avoid**

- Full-screen gradients, glassmorphism stacks, or “dashboard template” clutter unrelated to the task  
- Auto-playing transitions between steps  
- Dark/light theme toggle in v1 (pick one readable light theme unless user requests otherwise)  

**v1 layout sketch**

```
┌──────────────────────────────────────────────────────────────┐
│  Config Builder          [metadata ▾]     Step 3 of 8        │
├──────────────┬───────────────────────────────────────────────┤
│  Stepper     │  Main panel (current step form)               │
│  ● Setup     │                                               │
│  ● Upload    │                                               │
│  ○ Filters   │                                               │
│  …           │                                               │
├──────────────┤                                               │
│  Available   │                                               │
│  columns     │                                               │
│  (context)   │                                               │
└──────────────┴───────────────────────────────────────────────┘
│  [← Back]                              [Continue →]          │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Wizard flow

Linear wizard with **Back** navigation. Metadata editable from a persistent **Settings** panel at any step.

```
┌─────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────┐
│ 1. Setup    │ → │ 2. Upload    │ → │ 3. Per-source  │ → │ 4. Joins     │
│ metadata,   │   │ sources +    │   │ pre-filters    │   │ (if N>1)     │
│ N sources,  │   │ empty targets│   │                │   │              │
│ M targets,  │   │              │   │                │   │              │
│ paths       │   │              │   │                │   │              │
└─────────────┘   └──────────────┘   └────────────────┘   └──────────────┘
       ↓
┌─────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────┐
│ 5. Derive   │ → │ 6. Post-     │ → │ 7. Map to      │ → │ 8. Review    │
│ columns     │   │ filters      │   │ target(s)      │   │ JSON +       │
│             │   │              │   │ per blueprint  │   │ download     │
└─────────────┘   └──────────────┘   └────────────────┘   └──────────────┘
```

### Step 1 — Setup

- `migration_id`, `client_id`, `version` — **defaults provided**, user may change **any time** (settings drawer / header).
- Count: **N source files**, **M target files**.
- **Connection paths:** user may set `base_path` and `target_path`; if omitted, default to the directory where files were uploaded (BE stores upload session path; generated config uses that path).
- Option: **Load existing config.json** to populate wizard (edit mode).

### Step 2 — Upload files

| Upload | Rules |
|---|---|
| Source CSVs (N) | Must have header row + data rows; infer column names (and sample types). |
| Target CSVs (M) | **Headers define columns.** If the file contains data rows, only the header row is kept and the user sees a truncation warning. |

- Auto-suggest **alias** per source from filename (editable).
- Show schema preview table per file.

### Step 3 — Pre-filters (per source, before join)

User configures filters **per source file** to reduce rows **before** that source participates in joins.

| Source role | UI behaviour | Generated config |
|---|---|---|
| **Root table** | Predicate / group / expression builder from that source’s columns | `blueprint.pre_filters` |
| **Join tables** | Same UI per join file | `joins[].pre_filters` |

Only show columns from the relevant source (with alias prefix in generated JSON).

### Step 4 — Joins (when blueprint uses 2+ sources)

- Sequential joins matching engine order (array order in `sources.joins`).
- User picks: `join_type` (dropdown), join file, alias, conditions from **column dropdowns** (predicates with operators; literal or column right-hand side).
- At least one **merge key** per join: `==` with `right_type: column` on both sides. Additional conditions are post-merge filters.
- **Not in UI v1:** expression-form join keys; `deriv.*` references (derivations run after joins).
- Conditions: predicate or AND/OR groups; operators from supported set (§2.5 parent doc).
- **No advanced join types** beyond engine (no arbitrary join graphs).

**Per blueprint:** user selects which sources belong to this blueprint (supports use case C). Sources not in a blueprint are omitted from that blueprint’s `sources` block.

### Step 5 — Derivations

- Add derivation rows: `EXPRESSION` | `REGEXP_REPLACE` | `CASE`.
- **Expression levels** (all three, as recommended):
  - **Simple:** column pickers, literals, operators via dropdowns.
  - **Medium:** CASE branches, REGEXP_REPLACE pattern/replacement fields.
  - **Advanced:** guarded free-text pandas expression (with safety hints; same rules as engine).
- Show live **available columns** list (`alias.column` + `deriv.*`).

### Step 6 — Post-filters

- Applied on **mapped target columns** (engine runs post-filters after mappings; wizard keeps user-facing order: derive → post-filter → map).
- Predicate, group, or expression forms (expression uses unqualified target column names per engine rules).

**Wizard UX order (fixed):** derive → post-filter → map. The BE emits config in engine order; post-filter rules reference target column names from empty CSV headers collected in step 2.

### Step 7 — Map to target (per blueprint)

For each of M blueprints / target files:

| Mapping option | UI |
|---|---|
| DIRECT | Source column dropdown (`alias.column`) |
| DERIVED | Derivation dropdown (`deriv.name`) |
| EXPRESSION | Simple/medium/advanced builder |
| `default_value` | Optional literal when source is null |
| `cast_to` | Dropdown: `str` \| `int64` \| `float64` \| `datetime64[ns]` |
| `is_nullable` | Checkbox |

**Type inference (best practice):**

- Infer `cast_to` from source sample values (integer → `int64`, float → `float64`, date-like → `datetime64[ns]`, else `str`).
- User can override per column.
- Target-only columns (no source): EXPRESSION or literal; default `is_nullable: true` unless user sets default.

**Use case D:** same source file selected as root for multiple blueprints; different mapping sets per target.

**Use case C:** each blueprint picks its own source subset and target file.

### Step 8 — Review & export

- Pretty-printed JSON preview.
- G0 validate via BE (`POST /api/v1/config/validate` or similar).
- Download `config.json`.
- Optional: save session server-side (later).

---

## 5. Edit existing config

- **Load** `config.json` → BE parses → FE hydrates wizard state.
- User can change any step and re-export.
- Round-trip must preserve valid configs produced by the engine (lossless for UI-supported features).

---

## 6. Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | User sets N sources and M targets; M = number of blueprints. |
| FR-2 | Target uploads use headers only; data rows are stripped with a clear warning. |
| FR-3 | Support use cases A, B, C, D per parent §1.1. |
| FR-4 | Pre-filter configuration per source; root filters emitted to `pre_filters`. |
| FR-5 | Join configuration via dropdowns (columns, operators, join types, aliases). |
| FR-6 | Derivations: EXPRESSION, REGEXP_REPLACE, CASE (simple + medium + advanced). |
| FR-7 | Post-filters on target schema. |
| FR-8 | Per-blueprint mappings to target headers with cast, nullable, default. |
| FR-9 | Metadata defaults editable at any step. |
| FR-10 | Connection paths user-configurable; default to upload directory. |
| FR-11 | Preview JSON + G0 validation before download. |
| FR-12 | Load and edit existing config files. |
| FR-13 | FE communicates with BE only via REST API (no direct engine imports in FE). |

---

## 7. Non-goals (v1)

- Running transforms inside config UI (link to main API later).
- Authentication / multi-user persistence.
- Non-CSV formats.
- Join graphs beyond sequential joins in `sources.joins`.

---

## 8. Engine dependencies & gaps

### 8.1 Pre-filter on join sources before merge

**Requirement:** pre-filter must reduce data **before join** for **each** source.

| Source | Config field | Engine behaviour |
|---|---|---|
| Root table | `blueprint.pre_filters` | Applied after root extract, before any join |
| Join tables | `joins[].pre_filters` | Applied after join file read, before merge |

References in join `pre_filters` must use that join's `alias` only (e.g. `dept.status`).

### 8.2 Post-filter timing

Engine applies `post_filters` **after** `mappings`. UI collects post-filter rules against target column names; BE generates config in correct order.

---

## 9. Backend API (draft)

Prefix e.g. `/api/v1/`. Exact paths TBD at implementation.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/session` | Create upload session; return session id |
| `POST` | `/session/{id}/sources` | Upload source CSV; return inferred schema |
| `POST` | `/session/{id}/targets` | Upload empty target CSV; return headers |
| `GET` | `/session/{id}` | Get wizard state |
| `PUT` | `/session/{id}/metadata` | Update migration_id, paths, etc. |
| `PUT` | `/session/{id}/blueprints/{bp}` | Update blueprint slice (filters, joins, …) |
| `POST` | `/config/validate` | G0 validate JSON |
| `POST` | `/config/generate` | Build config JSON from session |
| `POST` | `/config/import` | Load existing JSON into session |
| `GET` | `/config/export` | Download generated JSON |

---

## 10. Frontend screens (summary)

1. **Setup** — counts, metadata, paths, import config  
2. **Upload** — drag/drop sources + targets, alias edit, schema tables  
3. **Pre-filters** — accordion per source  
4. **Joins** — per blueprint, join chain builder  
5. **Derivations** — row editor with type selector  
6. **Post-filters** — target-column rules  
7. **Mappings** — grid: target column ← source / deriv / expression  
8. **Review** — JSON preview, validation status, download  

Persistent: **settings bar** (metadata + paths).

---

## 11. Acceptance criteria (v1)

### Functional

- [ ] User can create config for use case A (1 source, 1 target) and download valid JSON.
- [ ] User can create use case B (join, 1 target).
- [ ] User can create use case C (2+ blueprints, different sources).
- [ ] User can create use case D (2+ blueprints, same source, different mappings).
- [ ] Empty target CSV with headers only is enforced.
- [ ] Loaded config round-trips through edit flow.
- [ ] G0 validation passes on exported JSON for all supported scenarios.
- [ ] FE has zero dependency on `csv_data_transformer` Python package.

### UX / visual

- [ ] Wizard stepper and section layout match §3.4 (structured, not plain defaults).
- [ ] Visual design stays restrained — no heavy marketing-style or overly flashy styling.
- [ ] User always sees current step, progress, and validation feedback without hunting for errors.
- [ ] “Available columns” (or equivalent) context visible during filter/join/derive/map steps.

---

## 12. References

- Product spec: [`codeSanityGuilinesForAI.md`](codeSanityGuilinesForAI.md) — AI implementation rules (UX, FE, BE, errors, tests)
- Parent use cases: [`docs/REQUIREMENTS.md` §1.1](../docs/REQUIREMENTS.md)
- Config template: [`docs/CONFIG_TEMPLATE.md`](../docs/CONFIG_TEMPLATE.md)
- JSON Schema: [`schema/config.schema.json`](../schema/config.schema.json)
- Working examples: [`sampleConfig.json`](../sampleConfig.json), [`samples/manual_advanced/`](../samples/manual_advanced/README.md)
