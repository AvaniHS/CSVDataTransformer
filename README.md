# CSV Data Transformer

Configuration-driven, API-first CSV ETL engine. Upload a JSON config and source CSV files; receive one or more transformed CSV outputs.

## Features

- JSON-driven blueprints with direct mapping, joins, filters, derivations, and expressions
- Fail-first validation gates (G0–G5)
- REST API with Swagger UI
- CLI for local development and testing
- Single CSV response (1 blueprint) or ZIP archive (2+ blueprints)

## Requirements

- Python 3.11+ (3.12 recommended)

## Install

```bash
py -3.12 -m pip install -e ".[dev]"
```

## Quick Start — CLI

Place source files under the connection `base_path` configured in your JSON (see `sampleConfig.json`). Ensure target files are absent or empty.

```bash
# Validate config and source files (G0 + G1)
py -3.12 -m csv_data_transformer validate --config sampleConfig.json

# Run all blueprints
py -3.12 -m csv_data_transformer run --config sampleConfig.json

# Dry-run: execute transforms without writing targets (G4 nullable checks still run)
py -3.12 -m csv_data_transformer run --config sampleConfig.json --dry-run --log-level DEBUG
```

Outputs are written to the connection `target_path` from config (default `./data/output/`).

## Quick Start — API

Start the server:

```bash
py -3.12 -m uvicorn csv_data_transformer.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### Swagger / OpenAPI

| URL | Purpose |
|---|---|
| http://localhost:8000/api/v1/docs | Swagger UI |
| http://localhost:8000/api/v1/redoc | ReDoc |
| http://localhost:8000/api/v1/openapi.json | OpenAPI schema |

### Health check

```bash
curl http://localhost:8000/api/v1/health
```

### Transform (multipart upload)

Full `sampleConfig.json` with both blueprints — upload `employees.csv` and `departments.csv`:

```bash
curl -X POST http://localhost:8000/api/v1/transform \
  -F "config=@sampleConfig.json;type=application/json" \
  -F "files=@data/input/employees.csv" \
  -F "files=@data/input/departments.csv" \
  -o transformed_outputs.zip
```

Single-blueprint configs return one CSV (`Content-Type: text/csv`). Multi-blueprint configs return a ZIP.

### Validate only

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -F "config=@sampleConfig.json;type=application/json" \
  -F "files=@data/input/employees.csv" \
  -F "files=@data/input/departments.csv"
```

## Configuration

See `sampleConfig.json` for the reference direct-mapping config and [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) for the full specification.

### Top-level structure

| Field | Description |
|---|---|
| `migration_id` | Unique run identifier (logging, API headers) |
| `client_id` | Tenant/client identifier |
| `connections` | Named local file directory connections |
| `blueprints` | One or more independent transform pipelines |

### Blueprint basics

Each blueprint defines:

- `sources` — root CSV + optional joins
- `mappings` — target column definitions
- `target` — single output CSV filename
- Optional `pre_filters`, `derivations`, `post_filters`

Column references use dot notation in config (`emp.first_name`) and double-underscore physical names in the engine (`emp__first_name`).

### Sample blueprints

| Blueprint ID | Sources | Output |
|---|---|---|
| `bp_direct_one_source_one_target` | `employees.csv` | `employees_export.csv` |
| `bp_direct_two_sources_one_target` | `employees.csv` + `departments.csv` (LEFT join) | `employees_with_department.csv` |

## Project Layout

```
docs/             # REQUIREMENTS.md, AI coding guidelines, extensibility notes
csv_data_transformer/
├── api/          # FastAPI routes, schemas, workspace
├── config/       # JSON config models and G0 validation
├── connections/  # Path resolution
├── io/           # CSV readers/writers, file guards
├── engine/       # Pandas execution engine
├── pipeline/     # Orchestrator, blueprint runner, validators
└── audit/        # Logging
```

## Testing

```bash
py -3.12 -m pytest tests -v
```

## Extensibility

See [docs/extensibility.md](docs/extensibility.md) for how new file formats (e.g. XLSX) plug in without changing the orchestrator.

## License

Internal / project use — see repository owner for terms.
