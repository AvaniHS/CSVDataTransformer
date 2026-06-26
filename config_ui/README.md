# Config UI

Web wizard for building CSV Data Transformer config JSON files.

## Status

**v1 implemented** — FastAPI backend + React wizard frontend.

| Document | Purpose |
|---|---|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | Product spec |
| [`codeSanityGuilinesForAI.md`](codeSanityGuilinesForAI.md) | AI / implementation rules |

## Layout

```
config_ui/
├── backend/          # FastAPI (port 8002)
├── frontend/         # React + Vite (port 5173)
├── requirements.txt
└── run-dev.ps1
```

## Prerequisites

- Python 3.11+ with parent package installed: `py -3.12 -m pip install -e ".[dev]"`
- Node.js 18+ for the frontend

## Install

```powershell
# From repo root
py -3.12 -m pip install -r config_ui/requirements.txt
py -3.12 -m pip install -e ".[dev]"

cd config_ui/frontend
npm install
```

## Run (development)

**Backend** (from repo root):

```powershell
py -3.12 -m uvicorn config_ui.backend.app:app --host 0.0.0.0 --port 8002 --reload
```

- Swagger: http://localhost:8002/api/v1/docs

**Frontend** (proxies `/api` to backend):

```powershell
cd config_ui/frontend
npm run dev
```

- App: http://localhost:5173

Or use `.\config_ui\run-dev.ps1` to start both (backend in background).

## Tests

```powershell
py -3.12 -m pytest config_ui/backend/tests -q
```

## Related docs (parent project)

| Document | Purpose |
|---|---|
| [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) §1.1 | Use cases A–D |
| [`../schema/config.schema.json`](../schema/config.schema.json) | Output JSON Schema |
| [`../docs/CONFIG_TEMPLATE.md`](../docs/CONFIG_TEMPLATE.md) | Config field reference |
