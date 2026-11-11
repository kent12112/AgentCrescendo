# Six-week implementation plan

Capacity: approximately eight hours per week, 48 hours total. This is a constrained portfolio release, not a production platform. Each week ends with a demonstrable slice. If core work overruns, defer optional UI and replay features before weakening isolation or recovery claims.

Design reference: [visual architecture and technical decisions](visual-architecture.md).

## Week 1 — One useful, constrained desktop agent

* Set up Next.js, FastAPI, Python tooling, PostgreSQL migrations, and Docker Compose.
* Connect one E2B desktop and expose an authenticated live view.
* Implement a small explicit observe/act loop through the gateway; keep secrets outside the desktop.
* Add task identities, destination restrictions, deadline/step limits, and desktop cleanup from the outset.
* Evaluate two model candidates on a small fixed research task and record cost/latency.

Exit: one agent researches a public source and returns a cited result. Prove permitted browsing works and private/backend network destinations are blocked. Confirm E2B networking and live-view access fit the security design; resolve gaps before adding workers.

## Week 2 — Durable run lifecycle

* Add Temporal workflow and activities, stable start IDs, heartbeats, bounded retry, and cancellation.
* Persist run/task state, findings, artifacts, and desktop leases.
* Add usage reservations, usage reconciliation, and a resource reaper.
* Exercise worker termination and replacement-desktop recovery early.

Exit: stop a worker during a research task and recover from persisted progress. Cancellation and timeout leave no indefinitely running desktops.

## Week 3 — Real agent communication

* Add dynamic task DAG generation and validation, with at most three active desktops.
* Implement message schemas, transactional outbox, dispatcher, and deduplication.
* Add versioned proposals, conditional acceptance transactions, and structured objections.
* Permit bounded reassignment and follow-up tasks as findings arrive.

Exit: workers exchange a finding and a handoff; duplicate delivery changes state once. Concurrent incompatible proposals produce an explicit conflict and reevaluation.

## Week 4 — Useful end-to-end experience

* Build prompt interpretation, missing-information clarification, and run commands.
* Add task status, message timeline, artifact access, and resumable SSE events.
* Complete the weekend-trip benchmark with provenance, budget/timing checks, and partial-result handling.
* Run a product-comparison task using the same runtime to check generality.

Exit: a user can submit, watch, redirect, and finish a run. Reconnecting the dashboard preserves the run and event history.

## Week 5 — Security and failure evidence

* Add controlled malicious-page and malicious-message fixtures with synthetic secrets.
* Test cross-run access, stale proposals, duplicate messages, limits, cancellation, and recovery.
* Instrument distributed traces and summarize cost, latency, task success, recovery outcomes, and blocked actions.
* Implement 24-hour retention and user-requested deletion, including artifact access invalidation.

Exit: reproducible tests support each stated security and reliability claim. Document observed limitations and provider retention separately.

## Week 6 — Private beta and portfolio

* Package one-command local startup, environment documentation, and architecture diagrams.
* Choose a hosted configuration only after measuring its recurring cost; preserve local deployment if the budget cannot cover safe hosting.
* Invite a small tester group if hosting is viable; record bugs and measured runs.
* Record a short live-task demo and a separate failure/security walkthrough.
* Write a clear README and resume bullets backed by actual measurements.

Exit: reproducible local release, sourced everyday-task demo, failure/security evidence, and an invite-only deployment if affordable.

## Repository layout

```text
apps/web/                 Next.js dashboard
services/api/             FastAPI endpoints and SSE
services/workers/         Temporal workflows and activities
packages/contracts/      JSON schemas and generated TypeScript types
packages/agent_runtime/   Agent loop, model adapter, desktop tools
packages/security/       Identity, authorization, destination policy
packages/persistence/    SQLAlchemy models, migrations, outbox
evals/                   Task fixtures, attack fixtures, benchmark runner
infra/                   Compose and deployment configuration
docs/                    Architecture, setup, evidence, demo script
```

These are logical modules, not an instruction to deploy a microservice for every directory. Start with API and worker processes, one gateway module, and one database server with separately owned data.

## Explicit deferrals

Full video replay, billing, team workspaces, arbitrary logged-in browsing, reservations, purchases, autonomous publishing, custom VM infrastructure, Kafka/RabbitMQ, Kubernetes, multiple agent frameworks, and elaborate dashboard animation.

Live desktops, task status, agent communication, and sourced final artifacts remain the essential demo surface.

## Portfolio claims to earn

* Built a general-purpose multi-agent workspace with isolated desktops, structured communication, and durable orchestration.
* Implemented transactional message delivery, idempotent consumers, and optimistic concurrency for shared plans.
* Demonstrated worker-failure recovery and enforced scoped permissions against reproducible adversarial scenarios.

Add numerical improvements only after collecting results. Describe the actual tested boundary rather than claiming universal prompt-injection prevention or exactly-once desktop execution.
