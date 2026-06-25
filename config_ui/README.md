# Config UI

Web wizard for building CSV Data Transformer config JSON files.

## Status

**Requirements captured** — see [`REQUIREMENTS.md`](REQUIREMENTS.md) for the full spec (wizard flow, use cases C/D, BE/FE split, UX principles §3.4).

**AI / implementation guidelines** — see [`codeSanityGuilinesForAI.md`](codeSanityGuilinesForAI.md) (architecture, UX, FE, BE, errors, tests).

## Planned layout

```
config_ui/
├── REQUIREMENTS.md      # Product spec
├── requirements.txt     # Python BE dependencies
├── backend/             # FastAPI (TBD)
└── frontend/            # React + Vite (TBD)
```

## Related docs (parent project)

| Document | Purpose |
|---|---|
| [`../docs/REQUIREMENTS.md`](../docs/REQUIREMENTS.md) §1.1 | Use cases A–D |
| [`../schema/config.schema.json`](../schema/config.schema.json) | Output JSON Schema |
| [`../docs/CONFIG_TEMPLATE.md`](../docs/CONFIG_TEMPLATE.md) | Config field reference |
