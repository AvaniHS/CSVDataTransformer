# Config File Template — Standard Reference

Documentation-only reference for the CSV Data Transformer JSON config. **Not runnable as-is** — replace every `<placeholder>` with real values and remove blueprints you do not need.

| Artifact | Purpose |
|---|---|
| [`schema/config.template.json`](../schema/config.template.json) | Structural template with placeholders |
| [`schema/config.schema.json`](../schema/config.schema.json) | Machine-readable JSON Schema (IDE validation) |
| [`sampleConfig.json`](../sampleConfig.json) | Minimal working direct-mapping example |
| [`samples/manual_advanced/`](../samples/manual_advanced/README.md) | Working advanced example (joins, CASE, etc.) |

---

## Top-level fields

| Field | Required | Place your value |
|---|---|---|
| `$schema` | No | Path to JSON Schema, e.g. `./schema/config.schema.json` |
| `migration_id` | Yes | Unique run identifier (logging, API headers) |
| `client_id` | Yes | Tenant / client identifier |
| `version` | Yes | Config document version, e.g. `1.0.0` |
| `connections` | Yes | Named connection objects (at least one) |
| `blueprints` | Yes | Array of pipeline definitions (at least one) |

---

## Connections

Each key under `connections` is a name you reference as `connection_ref` in blueprints.

| Field | Required | Place your value |
|---|---|---|
| `type` | Yes | `LOCAL_FILE_DIRECTORY` (alias `LOCAL_CSV_DIRECTORY` accepted) |
| `base_path` | Yes | Directory containing **source** CSV files |
| `target_path` | Yes | Directory for **output** CSV files |
| `file_options.format` | No | `CSV` (default) |
| `file_options.encoding` | No | e.g. `utf-8` |
| `file_options.delimiter` | No | e.g. `,` |
| `file_options.quote_char` | No | e.g. `"` |
| `file_options.header_row` | No | `true` / `false` |
| `file_options.max_file_size_mb` | No | Integer, default `100` |

---

## Blueprint

Each blueprint = one independent pipeline → **exactly one target CSV**.

| Field | Required | Place your value |
|---|---|---|
| `sequence_order` | Yes | Integer ≥ 1; lower runs first |
| `blueprint_id` | Yes | Stable id for logs and errors |
| `comment` | No | Human-readable note |
| `sources` | Yes | Root table + optional joins |
| `pre_filters` | No | Default `[]` — filters before joins |
| `derivations` | No | Default `[]` — calculated columns |
| `post_filters` | No | Default `[]` — filters after mappings |
| `target` | Yes | Output file definition |
| `mappings` | Yes | Target column definitions (≥ 1) |

### Use cases (blueprint patterns)

| Use case | Sources | Outputs |
|---|---|---|
| **A** — Single file | 1 root, no joins | 1 CSV |
| **B** — Multi-file join | 1 root + 1..N joins | 1 CSV |
| **C** — Multi-output | Different sources per blueprint | 2+ CSVs (ZIP from API) |
| **D** — Source split | Same root file, different blueprints | 2+ CSVs |

---

## Sources

### Root table

| Field | Required | Place your value |
|---|---|---|
| `connection_ref` | Yes | Key from `connections` |
| `file_name` | Yes | Source CSV filename only |
| `alias` | Yes | Short prefix, unique in blueprint |
| `comment` | No | Optional note |

Column reference in config: `{alias}.{column}` → engine physical name `{alias}__{column}`.

**Ignored source columns:** Any column in the CSV that is not referenced in mappings (or derivations/filters) is never written to the target.

### Joins (optional)

| Field | Required | Place your value |
|---|---|---|
| `join_type` | Yes | `LEFT` \| `INNER` \| `RIGHT` \| `OUTER` |
| `connection_ref` | Yes | Connection key |
| `file_name` | Yes | Join CSV filename |
| `alias` | Yes | Unique alias for join table |
| `conditions` | Yes | Array of predicates and/or groups |
| `pre_filters` | No | Filters on join table after read, before merge (this join's `alias` only) |
| `comment` | No | Optional note |

Root `pre_filters` run before joins. Join `pre_filters` run after the join file is read, before merge.

---

## Predicates and condition groups

Used in: join `conditions`, `pre_filters`, `post_filters` (predicate/group only), CASE `when` branches.

### Predicate form

```json
{
  "left": "<alias.column>",
  "operator": "<operator>",
  "right": "<literal or alias.column>",
  "right_type": "literal"
}
```

| Operator | Aliases | `right` required |
|---|---|---|
| `==` | `=`, `EQ` | Yes |
| `!=` | `<>`, `NE` | Yes |
| `<` | `LT` | Yes |
| `<=` | `LE` | Yes |
| `>` | `GT` | Yes |
| `>=` | `GE` | Yes |
| `IN` | | Yes (array) |
| `NOT_IN` | `NOT IN` | Yes (array) |
| `LIKE` | | Yes (pattern with `%`, `_`) |
| `NOT_LIKE` | `NOT LIKE` | Yes |
| `IS_NULL` | `IS NULL` | No |
| `IS_NOT_NULL` | `IS NOT NULL` | No |

**`right_type`:** `literal` (constant) or `column` (qualified `alias.column`).

### Group form (AND / OR)

```json
{
  "logic": "AND",
  "conditions": [
    { "left": "<alias.column>", "operator": "==", "right": "<value>", "right_type": "literal" }
  ]
}
```

Groups may nest inside join conditions and CASE `when` branches.

### Expression filter form

Used in `pre_filters` and `post_filters` only.

```json
{
  "type": "expression",
  "value": "<pandas expression using alias__column physical names>"
}
```

**Pre-filters:** expression uses working DataFrame columns (`ord__qty > 0`).

**Post-filters:** run **after mappings** on the target DataFrame — use **unqualified target column names** (`line_amount > 0`).

---

## Derivations

Evaluated sequentially. Variable `foo` → physical column `deriv__foo` → reference in mappings as `deriv.foo`.

### EXPRESSION

```json
{
  "variable_name": "<name>",
  "transform_type": "EXPRESSION",
  "expression": "<pandas expression using alias.column or deriv.other>",
  "comment": "<optional>"
}
```

### REGEXP_REPLACE

```json
{
  "variable_name": "<name>",
  "transform_type": "REGEXP_REPLACE",
  "source": "<alias.column>",
  "pattern": "<regex>",
  "replacement": "<string>",
  "comment": "<optional>"
}
```

### CASE

```json
{
  "variable_name": "<name>",
  "transform_type": "CASE",
  "branches": [
    {
      "when": { "left": "<alias.column>", "operator": "==", "right": "<literal>", "right_type": "literal" },
      "then": "<literal, alias.column, or expression>"
    }
  ],
  "else": "<optional fallback>",
  "comment": "<optional>"
}
```

---

## Mappings

Each entry produces **one target column**. Only mapped columns appear in the output file.

| Field | Required | Place your value |
|---|---|---|
| `target_column` | Yes | Output column name (no alias prefix) |
| `source_type` | Yes | `DIRECT` \| `DERIVED` \| `EXPRESSION` |
| `source_value` | Yes | See table below |
| `cast_to` | Yes | `str` \| `int64` \| `float64` \| `datetime64[ns]` |
| `is_nullable` | Yes | `false` = abort if null after cast; `true` = allow empty |
| `default_value` | No | Literal applied when source is null (before nullable check) |

| `source_type` | `source_value` |
|---|---|
| `DIRECT` | Qualified column, e.g. `ord.email` |
| `DERIVED` | Derivation ref, e.g. `deriv.line_amount` |
| `EXPRESSION` | Pandas expression, e.g. `ord.qty * ord.unit_price` or `'HARDCODED'` |

### Common mapping scenarios

| Scenario | Example |
|---|---|
| Direct copy | `"source_type": "DIRECT", "source_value": "ord.id"` |
| Rename via mapping | `"target_column": "employee_id", "source_value": "ord.id"` |
| Null → default | `"default_value": "unknown@example.com", "is_nullable": false` |
| Nullable empty cell | `"is_nullable": true` (no default) |
| Join column (nullable on LEFT join) | `"source_value": "dept.name", "is_nullable": true` |
| From derivation | `"source_type": "DERIVED", "source_value": "deriv.status_tier"` |
| Computed at map time | `"source_type": "EXPRESSION", "source_value": "ord.qty * ord.unit_price"` |
| Hardcoded constant | `"source_type": "EXPRESSION", "source_value": "'MY_SOURCE'"` |
| Synthetic null column | `"source_type": "EXPRESSION", "source_value": "ord.qty.where(ord.qty < 0)", "is_nullable": true` |

**Extra target column with no source analogue:** use `EXPRESSION` with a constant or an expression that evaluates to null; set `is_nullable` accordingly.

---

## Target

| Field | Required | Place your value |
|---|---|---|
| `connection_ref` | Yes | Connection key (uses `target_path`) |
| `file_name` | Yes | Output CSV filename |
| `comment` | No | Optional note |

Target file must **not exist** or must be **empty** before each run.

---

## Pipeline order (per blueprint)

```
pre_filters → joins (in order) → derivations → mappings → post_filters → write
```

---

## API upload notes

- Upload union of all `file_name` values across every blueprint (root + joins), deduplicated.
- Each uploaded filename must match a `file_name` in the config.
- 1 blueprint → API returns single CSV; 2+ blueprints → ZIP.

---

## Quick start from template

1. Copy `schema/config.template.json` to your working config path.
2. Replace all `<placeholders>`.
3. Delete reference / unused blueprint blocks.
4. Validate: `py -3.12 -m csv_data_transformer validate --config <your-config.json>`
5. Run: `py -3.12 -m csv_data_transformer run --config <your-config.json>`
