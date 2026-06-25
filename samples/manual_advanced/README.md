# Manual Advanced Test Sample

Self-contained fixtures for **manual** end-to-end testing of joins, derivations, filters, and null/default handling.

## Layout

```
samples/manual_advanced/
├── config.json              # Blueprint config
├── input/
│   ├── sales_orders.csv     # Root source (extra columns intentionally not mapped)
│   ├── products.csv         # LEFT join #1
│   └── regions.csv          # LEFT join #2
├── expected/
│   └── sales_enriched_export.csv   # Reference output (4 rows)
└── output/                  # CLI writes here (delete output file before re-run)
```

## What this exercises

| Feature | How it appears in this sample |
|---|---|
| **Two LEFT joins** | `products` on `product_sku`, `regions` on `region_code` |
| **Ignored source columns** | `sales_rep_id`, `internal_margin_pct`, `raw_checksum`, `supplier_id`, `tax_rate`, `fiscal_zone_id`, etc. never mapped |
| **Pre-filters** | Drops `CANCELLED` orders (1004) and `qty = 0` (1005) |
| **EXPRESSION derivation** | `line_amount = qty * unit_price` |
| **REGEXP_REPLACE** | `phone_digits` strips non-digits; `email_domain` strips local part |
| **CASE derivation** | `status_tier`: ACTIVE→PREMIUM, PENDING→STANDARD, else OTHER |
| **Post-filter (expression)** | `line_amount > 0` on mapped target columns |
| **Null email + default** | Orders 1002, 1006 → `no-email@placeholder.com` |
| **Empty phone + default** | Order 1003 → `0000000000` |
| **Missing join (region)** | Order 1006 (`XX-INVALID`) → blank `region_name` |
| **Hardcoded target column** | `data_source` = `MANUAL_TEST` (EXPRESSION literal) |
| **Synthetic null column** | `future_expansion_field` — no source column; always empty |

## Input rows (6 orders)

| order_id | Notes |
|---|---|
| 1001 | Full data — all joins match |
| 1002 | Missing email — default applied |
| 1003 | Missing phone — default applied |
| 1004 | **Filtered out** — status CANCELLED |
| 1005 | **Filtered out** — qty = 0 |
| 1006 | Missing email + invalid region code — region_name empty |

## CLI

From the project root. **Delete the output file first** if re-running (target must be absent or empty).

```bash
py -3.12 -m csv_data_transformer validate --config samples/manual_advanced/config.json

py -3.12 -m csv_data_transformer run --config samples/manual_advanced/config.json
```

Output: `samples/manual_advanced/output/sales_enriched_export.csv` (4 rows).

Compare against `expected/sales_enriched_export.csv`.

## API (Swagger / curl)

Upload all three input CSVs plus `config.json`:

```bash
curl -X POST http://localhost:8001/api/v1/transform \
  -F "config=@samples/manual_advanced/config.json;type=application/json" \
  -F "files=@samples/manual_advanced/input/sales_orders.csv" \
  -F "files=@samples/manual_advanced/input/products.csv" \
  -F "files=@samples/manual_advanced/input/regions.csv" \
  -o sales_enriched_export.csv
```

Single blueprint → response is one CSV file (`text/csv`), not a ZIP.

## Target columns (12)

Only these columns appear in the output — nothing else from source files:

1. `order_id`
2. `customer_name`
3. `product_name` (from join; nullable)
4. `category` (from join; nullable)
5. `region_name` (from join; nullable)
6. `line_amount` (derived)
7. `status_tier` (CASE)
8. `phone_digits` (REGEXP_REPLACE + default)
9. `contact_email` (default for null)
10. `email_domain` (derived; empty when no email)
11. `data_source` (hardcoded)
12. `future_expansion_field` (synthetic; always empty with current data)
