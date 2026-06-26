# Async ETL Jobs — Queue, Concurrency & Live Progress (Brainstorm)

| Field | Value |
|---|---|
| Status | **Brainstorm / design exploration** — not implemented |
| Related | [`REQUIREMENTS.md`](REQUIREMENTS.md) §1.4 (v1 non-goals), §8 (sync API), §4 (checkpoint logs) |
| Parent engine | `csv_data_transformer` — fail-first, in-memory pandas, isolated workspace per run |

---

## 1. Problem statement

### 1.1 Today (v1)

| Aspect | Current behaviour |
|---|---|
| API model | **Synchronous** — client uploads config + CSVs, waits until transform completes |
| Timeout | Default **300 s** (`API_TIMEOUT_SEC`) |
| Concurrency | Multiple parallel HTTP calls each get an **isolated temp workspace** — no central queue |
| Progress | None over HTTP — only final CSV/ZIP or error JSON |
| Scale | In-memory pandas within `max_file_size_mb` per file |

Large ETL runs may exceed timeout. Many clients calling in parallel can exhaust **CPU, RAM, and disk** on one host. Users need:

1. **Accept work without blocking** until completion  
2. **Fair / controlled concurrency** (queue)  
3. **Live status** per job (and per blueprint)  
4. **Retrieve results** when ready  

This document explores options. **No decision is final** until product requirements are refined.

---

## 2. Goals & non-goals

### 2.1 Goals (candidate)

| ID | Goal |
|---|---|
| G1 | Submit transform asynchronously; receive a **job id** immediately |
| G2 | **Queue** excess work when workers are busy |
| G3 | Expose **queryable status** (phase, blueprint, row counts, errors) |
| G4 | Optional **live updates** (SSE/WebSocket) for UIs and integrations |
| G5 | Preserve v1 **fail-first** semantics — failed job = no partial success contract change unless explicitly designed |
| G6 | Keep **workspace isolation** — one job must not read/write another job’s files |
| G7 | Support **cancellation** of queued or running jobs (best-effort) |

### 2.2 Non-goals (for early async phases)

- Distributed Spark/Dask cluster execution  
- Cross-node file sharing without explicit object storage  
- Guaranteed exactly-once delivery at row level  
- Replacing synchronous `/transform` immediately (can coexist as “fast path” for small jobs)  

---

## 3. Job lifecycle (conceptual)

```
                    ┌──────────┐
         submit ──► │ QUEUED   │ ◄── backpressure / max queue depth
                    └────┬─────┘
                         │ worker available
                         ▼
                    ┌──────────┐
                    │ RUNNING  │──► progress events (G0…G5, blueprint, phase)
                    └────┬─────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌───────────┐
         │ SUCCESS│ │ FAILED │ │ CANCELLED │
         └────────┘ └────────┘ └───────────┘
              │          │
              ▼          ▼
         result URLs   error payload (gate, blueprint_id, message)
         TTL cleanup   workspace cleanup
```

**Suggested status enum:** `queued` | `running` | `succeeded` | `failed` | `cancelled`

**Sub-state for `running`:** mirror existing pipeline checkpoints (see §5).

---

## 4. Request queue — options

### 4.1 Comparison matrix

| Approach | Pros | Cons | Fits this project? |
|---|---|---|---|
| **A. In-process queue** (asyncio + `BackgroundTasks` / worker pool) | No new infra; simple for single-node | Dies with process; no cross-replica queue | Good for **dev / single server v2** |
| **B. Redis + RQ / ARQ / Celery** | Mature; horizontal workers; retries | Ops dependency (Redis); Celery heaviness | Good for **production single- or multi-node** |
| **C. DB-backed queue** (Postgres `SKIP LOCKED`, SQLite for small) | Durable; audit trail in one store | Worker polling; schema migration | Good if you already need a DB for jobs |
| **D. SQS / Azure Queue / GCP Pub/Sub** | Managed scale; cloud-native | Vendor lock-in; local dev harder | Good for **cloud deployment** |
| **E. Separate “worker” process + file drop** | Minimal deps | Race conditions; weak status model | Not recommended |

### 4.2 Recommended phasing (strawman)

| Phase | Queue | Workers | Status API |
|---|---|---|---|
| **2a** | In-process bounded queue (max N running, M queued) | Same uvicorn process or 1 sidecar worker | `GET /jobs/{id}` polling |
| **2b** | Redis + ARQ (or RQ) | 1..K worker processes | Polling + optional SSE |
| **2c** | Managed queue + object storage for artifacts | Autoscaling workers | Polling + SSE + webhooks |

**Principle:** API process **accepts** jobs and **reads status**; **workers execute** pipeline. Never run heavy pandas work on the API thread pool indefinitely.

### 4.3 Concurrency controls

| Knob | Purpose |
|---|---|
| `MAX_CONCURRENT_JOBS` | Cap simultaneous pipeline runs (protect RAM) |
| `MAX_QUEUE_DEPTH` | Reject with `503` / `429` when overloaded |
| `MAX_JOBS_PER_CLIENT` | Fairness by `client_id` (from config or API key later) |
| `JOB_PRIORITY` | Optional — ops migrations vs user retries |
| **Single-flight per `migration_id`** | Optional dedup — reject duplicate in-flight migration |

**Memory note:** Each job loads full CSVs in memory (v1). Queue depth × file size must fit host RAM — queue is not unbounded.

---

## 5. What to report as “live progress”

Reuse existing **checkpoint semantics** from [`REQUIREMENTS.md`](REQUIREMENTS.md) §4 (logging) and pipeline order — expose the same facts to clients.

### 5.1 Progress event model (draft)

```json
{
  "job_id": "job_abc123",
  "status": "running",
  "migration_id": "mig_demo",
  "blueprint_id": "bp_employees_export",
  "gate": "G2",
  "phase": "join",
  "message": "Completed join dept",
  "progress_pct": 45,
  "metrics": {
    "rows_before": 10000,
    "rows_after": 8500,
    "blueprint_index": 1,
    "blueprint_count": 2
  },
  "timestamp": "2026-06-26T12:00:00Z"
}
```

### 5.2 Suggested checkpoint sequence (per job)

| Order | Event | `phase` | Notes |
|---|---|---|---|
| 1 | Job accepted | `queued` | position in queue optional |
| 2 | G0/G1 pass | `validation` | config + files |
| 3 | Blueprint N start | `blueprint_start` | `sequence_order`, `blueprint_id` |
| 4 | Root extract | `extract` | row count, file size |
| 5 | Pre-filters | `pre_filter` | rows before/after |
| 6 | Join k | `join` | alias, row count |
| 7 | Derivations | `derivations` | count completed |
| 8 | Mappings | `mappings` | target column count |
| 9 | Post-filters | `post_filter` | rows before/after |
| 10 | Load / G5 | `load` | bytes written |
| 11 | Job complete | `complete` | links to outputs |

**`progress_pct`:** heuristic — e.g. `(completed_blueprints × 100 + step_weight) / total` — document as **approximate**, not SLA.

### 5.3 Failure events

On fail-first abort, emit terminal event with:

- `status: failed`
- `gate` (G0–G5)
- `blueprint_id`, `phase`, `expression` (if applicable)
- Same shape as v1 `ErrorResponse` for consistency

---

## 6. How clients get live status

### 6.1 Patterns

| Pattern | Mechanism | Best for |
|---|---|---|
| **Polling** | `GET /api/v1/jobs/{id}` every 1–5 s | Simple integrations, CLI |
| **SSE** | `GET /api/v1/jobs/{id}/events` (`text/event-stream`) | Web UI, live dashboards |
| **WebSocket** | Bidirectional; cancel command | Rich UI (more complex) |
| **Webhook** | `POST` to client URL on terminal state | Server-to-server |
| **Long poll** | Hold request until state change | Middle ground (less common today) |

**Recommendation:** Implement **polling first** (2a), add **SSE** for config UI / ops dashboard (2b). Webhooks optional for enterprise.

### 6.2 SSE sketch

```
event: progress
data: {"phase":"join","blueprint_id":"bp_1",...}

event: progress
data: {"phase":"mappings",...}

event: complete
data: {"status":"succeeded","download_url":"/api/v1/jobs/job_abc123/result"}
```

Client uses `EventSource` in browser; curl with `--no-buffer` for debugging.

---

## 7. API surface (draft)

Coexist with sync `/transform` for small jobs.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/jobs` | Submit config + files → `{ job_id, status: "queued" }` |
| `GET` | `/api/v1/jobs/{id}` | Current status + last event + summary metrics |
| `GET` | `/api/v1/jobs/{id}/events` | SSE stream (optional) |
| `GET` | `/api/v1/jobs/{id}/result` | Download CSV/ZIP when `succeeded` |
| `DELETE` | `/api/v1/jobs/{id}` | Cancel if queued; best-effort if running |
| `GET` | `/api/v1/jobs` | List jobs (filter by `client_id`, status) — ops only |

**Sync path (keep):** `POST /api/v1/transform` — if estimated size &lt; threshold, run inline; else `413`/`202` with hint to use `/jobs`.

---

## 8. Storage & artifacts

| Concern | Option |
|---|---|
| Job metadata | Redis hash / Postgres row / in-memory dict (dev only) |
| Event log | Redis stream / DB table append-only / file per job |
| Upload staging | Existing workspace pattern — `{workspace_root}/{job_id}/input/` |
| Output files | Workspace until TTL; then **object storage** (S3/Azure Blob) for multi-node |
| TTL | e.g. 24 h after complete — cron deletes workspace + metadata |

**Multi-worker rule:** Workers must share **visible storage** (NFS, S3 FUSE, or upload to blob at start) if API and worker are not the same machine.

---

## 9. Architecture diagrams

### 9.1 Single node (phase 2a)

```
┌─────────────┐     submit      ┌──────────────────┐
│   Client    │ ──────────────► │  FastAPI (API)   │
│             │ ◄── poll/SSE ── │  job registry    │
└─────────────┘                 └────────┬─────────┘
                                         │ enqueue
                                         ▼
                                ┌──────────────────┐
                                │  Worker pool     │
                                │  (N concurrent)  │
                                │  Orchestrator    │
                                └────────┬─────────┘
                                         │
                                         ▼
                                workspace/{job_id}/
```

### 9.2 Multi worker (phase 2b)

```
Clients ──► API ──► Redis (queue + pub/sub for events)
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Worker 1    Worker 2    Worker 3
          │           │           │
          └───────────┴───────────┘
                      │
              shared object storage (inputs/outputs)
```

---

## 10. Integration with config UI (future)

| Concern | Approach |
|---|---|
| Submit | Config UI calls `POST /jobs` instead of blocking transform |
| Progress | SSE or poll drives stepper / progress bar |
| Download | Enable “Download results” when `status === succeeded` |
| G0 errors | Fail at `queued` → `failed` before worker starts — same error shape |

---

## 11. Observability & ops

| Need | Tooling |
|---|---|
| Queue depth metric | Prometheus / logs: `jobs_queued`, `jobs_running` |
| Job duration | Histogram per blueprint count |
| Stuck jobs | Heartbeat from worker; requeue if silent &gt; T minutes |
| Audit | `migration_id`, `client_id`, `X-Request-Id` on every event |

Align log format with [`codeSanityGuilinesForAI.md`](codeSanityGuilinesForAI.md) — progress API is a **read model** over the same checkpoint facts.

---

## 12. Security & fairness (when auth arrives)

- Authenticate `POST /jobs`; scope list/get to owner or admin  
- Rate limit submissions per API key  
- Sanitize job ids (no path traversal in workspace)  
- Result download URLs: signed, time-limited tokens  

---

## 13. Open questions

| # | Question | Options |
|---|---|---|
| Q1 | Keep sync `/transform` forever or deprecate? | Dual path vs jobs-only |
| Q2 | Max queue depth behaviour? | 429 vs 503 vs synchronous fallback |
| Q3 | Partial blueprint success on multi-blueprint jobs? | v1 engine aborts all — async should match unless spec changes |
| Q4 | Progress storage retention? | Last event only vs full event log |
| Q5 | Chunked/larger-than-RAM files? | Separate “streaming ETL” initiative vs queue-only |
| Q6 | Priority queues for tenants? | Single FIFO vs weighted fair queue |
| Q7 | Idempotent resubmit same files + config? | New job id vs dedup hash |

---

## 14. Suggested next steps

1. **Product:** Define SLAs (max wait, max job size, retention).  
2. **Spike:** In-process queue + `GET /jobs/{id}` on a branch — measure RAM under parallel load.  
3. **Spec:** Add §9 “Async jobs” to [`REQUIREMENTS.md`](REQUIREMENTS.md) once approach chosen.  
4. **UI:** Config UI “Run transform” wired to jobs API when both exist.  

---

## 15. References

| Resource | Link |
|---|---|
| v1 API constraints | [`REQUIREMENTS.md`](REQUIREMENTS.md) §8.4 |
| v1 non-goals (sync only) | [`REQUIREMENTS.md`](REQUIREMENTS.md) §1.4 |
| Pipeline checkpoints | [`REQUIREMENTS.md`](REQUIREMENTS.md) §4, §7 |
| Error response shape | [`codeSanityGuilinesForAI.md`](codeSanityGuilinesForAI.md) §3.4 |
| Config UI (future run) | [`../config_ui/REQUIREMENTS.md`](../config_ui/REQUIREMENTS.md) |
