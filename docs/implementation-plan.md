# Six-week implementation plan

Capacity: approximately eight hours per week, 48 hours total. This is a constrained portfolio release, not a production platform. Each week ends with a demonstrable slice. If core work overruns, defer optional UI and replay features before weakening isolation or recovery claims.

Design reference: [visual architecture and technical decisions](visual-architecture.md).

## Learning and career objective

The builder enjoys learning deeply and is targeting applied AI engineering at Anthropic. This project should develop transferable engineering judgment and produce evidence of that judgment; it is not a claim about Anthropic's hiring requirements or a guarantee of employment.

Optimize for understanding, useful agent behavior, reliable execution, and measured security boundaries. Technology count is not a success metric. Keep the six-week release focused, and continue deeper experiments afterward rather than rushing through unfamiliar concepts.

### How to learn while building

Explain every Unix/shell command before running it: its purpose, important flags and operators, expected output, and whether it changes data. Relate the actual output to the concept being learned. Explain new commands fully; use short reminders for repeated commands. Introduce commands as part of the current task rather than overwhelming the learner with unrelated shell material. See [command reference](learning/02-terminal-commands.md).

For each milestone:

1. Explain the problem and predict the failure mode before implementing the solution.
2. Build a small working slice and inspect its messages, database changes, and traces.
3. Deliberately break it: kill a worker, repeat a message, inject malicious content, or change shared state concurrently.
4. Explain the observed behavior and compare it with the prediction.
5. Record the result, tradeoff, and remaining uncertainty in a short learning journal and architecture decision record.

Prefer coaching through consequential decisions over copying unexplained infrastructure. The builder should personally implement and explain representative pieces: one agent observe/act step, one tool authorization check, one transactional outbox operation, one conditional plan update, and one evaluation case. AI assistance can accelerate scaffolding and review while these exercises preserve hands-on understanding.

### Applied AI depth to demonstrate

| Area | Learning exercise | Evidence |
|---|---|---|
| Agent behavior | Inspect tool schemas, observation quality, context growth, termination, and replanning | Annotated traces of a successful run and a failed run |
| Evaluation | Define a small held-out task set, explicit rubrics, deterministic checks, and repeated trials | Versioned evaluation report with model/configuration, cost, latency, and failure categories |
| Baselines | Compare a single agent with the multi-agent system on equivalent tasks and budget | Explain when coordination helps and when it adds overhead |
| Experimentation | Change one factor at a time, such as tool description, screenshot strategy, or handoff schema | Before/after results with limitations and unsuccessful experiments retained |
| Security | Distinguish model compliance from externally enforced authority | Reproducible adversarial cases and a precise account of what was blocked |
| Distributed systems | Trace retries, duplicate delivery, stale updates, and recovery | Failure-injection walkthrough and architecture decisions |
| Product usefulness | Watch testers attempt actual everyday tasks | Concrete feedback, observed failures, and resulting changes |

Use deterministic assertions where possible and human review for subjective usefulness. If model-based grading is introduced, calibrate it against human judgments and do not treat the grader's output as ground truth. Avoid broad success claims from a tiny benchmark or tests used repeatedly for prompt tuning.

Keep a provider-neutral adapter. If Anthropic models are evaluated, learn their current official tool-use and computer-use interfaces directly and document integration choices; do not select a model solely because of the employer target. Provider selection remains benchmark-driven.

### Sustainable weekly allocation

Within the approximate eight-hour weekly budget, reserve about five hours for implementation, two for experiments and underlying concepts, and one for documenting and explaining results. Reduce optional feature scope when necessary to protect learning time. Revisit the timeline if an essential security or reliability requirement cannot be completed honestly within it.

Suggested portfolio artifacts: a working demo, readable source, architecture decision records, a concise threat model, reproducible evaluations, and a technical write-up explaining one difficult failure and its resolution. Resume claims must describe implemented behavior and measured results. Check current official job descriptions when preparing an actual application rather than assuming this plan mirrors a particular role.

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
