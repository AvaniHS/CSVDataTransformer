# Extensibility Review (SOLID)

This document confirms that v1 follows Open/Closed Principle for format and connection extensions.

## Adding XLSX (or another source format)

**No orchestrator edits required.** Add:

1. `io/readers/xlsx_reader.py` — implement `DataReader` ABC
2. Register in `DataReaderFactory.create()` for format `XLSX`
3. Optionally `io/writers/xlsx_writer.py` + `DataTargetFactory` for XLSX output

`BlueprintRunner` resolves readers/writers via factories using `connection.file_options.format`. The orchestrator only sequences blueprints and passes `input_dir` / `output_dir`.

## Adding YAML config

**No orchestrator edits required.** Add:

1. `config/yaml_reader.py` — implement `ConfigReader` ABC
2. Register in `ConfigReaderFactory.create()` for `.yaml` / `.yml`

## Adding database connections (future)

Would require:

1. New connection type in `connections/`
2. A `DataReader` that queries the source — still behind `DataReaderFactory`
3. G0 schema/validator updates for the new connection type

The orchestrator and API routes remain unchanged; they depend on `Orchestrator` and `PipelineConfig` abstractions only.

## Dependency direction

```
api/routes  →  pipeline/orchestrator  →  pipeline/blueprint_runner
                                         →  io/factories
                                         →  engine/PandasExecutionEngine
config/     →  (parsed once at boundary)
```

No layer below `pipeline/` imports from `api/`. No `api/` imports pandas.
