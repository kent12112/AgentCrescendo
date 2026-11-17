# 17. Starting a run exactly once

## The problem in one picture

Locked-room analogy: starting a run means unlocking one room and sending a worker
in. If the "start" button is pressed twice, we must not open a second room for
the same task.

```text
click, click, retry ──► API ──(1) save "starting" + workflow_id──► PostgreSQL
                          │
                          └─(2) start workflow "run-<run id>"──► Temporal
                                                                 one execution per ID
                          ◄─(3) accepted─────────────────────────┘
                          save "started"
```

The key: the workflow ID is the run ID with a prefix. Temporal refuses a second
execution with the same ID, so duplicates collapse into one, however they arrive.

## Prediction (before building)

With a random workflow ID per request, ten quick clicks would create ten
executions. With a stable ID, ten clicks should create one, and a crash between
steps 1 and 3 should be fixed by simply retrying.

## What we observed

| Experiment | Result |
| --- | --- |
| Random ID per request, 2 starts (control test) | 2 executions, activity ran twice: the bug we prevent |
| Stable ID, 5 concurrent + 1 late start (real Temporal, test) | 1 execution, activity ran once |
| Start after the workflow finished (test) | same execution returned; nothing re-ran |
| Live: 10 concurrent `curl` POSTs through the real API, worker, dev server | all `202`, 1 execution, activity ran once |
| Live: Temporal stopped, then POST | `503` after ~8.6 s; row kept `starting` + workflow ID |
| Live: Temporal restarted, POST again (twice) | `202`, same ID and original request time, 1 execution |

Matches the prediction. The surprise was in the migration, not Temporal: SQLite's
table rebuild keeps *named* constraints but drops *unnamed* ones, so the first
migration draft duplicated one check (caught by the migration test).

## Try it

```bash
.venv/bin/python scripts/temporal_dev_server.py          # terminal 1: Temporal on 127.0.0.1:7233
.venv/bin/python -m crescendo_workers.worker             # terminal 2: worker
TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest -q services/workers/tests
```

The web UI at http://127.0.0.1:8233 lists workflows; each run appears once as
`run-<run id>`.
