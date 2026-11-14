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

## Visual desktop experience

The intended experience is a real, watchable agent desktop: the user sees the
same E2B desktop the agent observes, and watches the agent scroll through web
pages while researching. This captures the user-requested Jonathan Mo-inspired
interaction direction; it does not claim to reproduce his implementation.

The core loop is:

```text
E2B desktop → screenshot → vision model proposes an action
                                 ↓
                         gateway authorization
                                 ↓
                     execute scroll on that desktop
                                 ↓
                      fresh screenshot → repeat / finish

User browser ← authenticated live stream ← same E2B desktop
```

The live stream is for the user; screenshots are separate model inputs. A
successful scroll API call is not proof that the page moved usefully: the next
screenshot must show the resulting state. Page text/search can supplement vision
for source extraction, but text-only success does not verify visual interaction.
Retrieved text and screen instructions remain untrusted; every action needs an
external permission check. Model and provider credentials stay on the host.

Week 1 proves screenshot observation, model-selected bounded scrolling, and
authenticated viewing on one desktop. The current vision fixture and text
research loop are separate implementations; combining permitted public-page
navigation, visual scrolling, and a cited answer is an explicit acceptance task.
Clicking, typing, arbitrary window control, and logged-in browsing are outside
this release's required scope. Add a new action only with its own authorization
and evaluation case. Week 4 integrates live viewing into the dashboard.

## Feature tracking

Use `[x]` only when a feature's stated acceptance check has evidence. An unchecked
item can have code implemented while live verification remains open. Keep detailed
results, ownership, and current blockers in [status](status.md), with links to
learning records or handoffs. Checklist IDs identify features; `W1-*` status IDs
identify remaining work and can cover several features.

Current checkmarks reflect recorded evidence as of November 13, 2026. Historical
test counts are evidence for their recorded revision, not a claim about every
later change. Preserve the exit criteria when reducing optional scope.

## Week 1 — One useful, constrained desktop agent

* Set up Next.js, FastAPI, Python tooling, PostgreSQL migrations, and Docker Compose.
* Connect one E2B desktop and expose an authenticated live view.
* Implement a small explicit observe/act loop through the gateway; keep secrets outside the desktop.
* Add task identities, destination restrictions, deadline/step limits, and desktop cleanup from the outset.
* Evaluate two model candidates on a small fixed research task and record cost/latency.

### Feature checklist

- [x] W1-F01: Local Next.js dashboard, FastAPI, Python tooling, PostgreSQL migrations, and Compose task-draft slice.
- [x] W1-F02: Create and delete persisted task drafts with validated limits and authenticated local API access.
- [x] W1-F03: Text observe/act loop with gateway-authorized navigation and public-source output; one user-reported Boston/Wikipedia run recorded.
- [x] W1-F04: Task identity, explicit tool grants, destination policy, bounded steps/deadline checks, and cleanup paths covered by local tests. Deadlines do not hard-interrupt in-flight SDK operations.
- [x] W1-F05: Real E2B screenshot sent as an image to a vision model; user-reported random-code recognition recorded.
- [x] W1-F06: Authorized host-driven scroll between screenshots; user-reported before/after code recognition recorded.
- [ ] W1-F07: Model chooses bounded scroll actions and correctly finishes the visual task; inspect saved model-input PNGs and record the live result.
- [ ] W1-F08: Authenticated live viewer renders the real desktop and visibly follows agent actions; proxy implementation/local tests exist, remote connection remains unresolved.
- [ ] W1-F09: Demonstrate the complete visual research slice on a permitted public page: navigate, observe screenshot, model-selected scroll, fresh observation, and source-supported cited answer. Record which tools supplied the answer evidence.
- [ ] W1-F10: Record controlled live allowed/blocked network results, browser redirects/subrequests, private/backend restrictions, IPv6/DNS behavior, and E2B exceptions. Resolve security gaps or explicitly narrow supported behavior before adding workers.
- [ ] W1-F11: Confirm provider-side desktop termination after normal completion and a deliberate failure; document the lifetime fallback and cleanup limits.
- [ ] W1-F12: Evaluate two model candidates on the same fixed research task and budget; record configuration, correctness, citation support, usage/cost, and latency.
- [ ] W1-F13: Save annotated successful/failed traces and a Week 1 decision record; update README to distinguish CLI execution from the draft-only dashboard.

Exit: one agent researches a public source using the visual loop and returns a cited result while the user watches its real desktop and scrolling. Prove permitted browsing works and private/backend network destinations are blocked. Confirm E2B networking and live-view access fit the security design; resolve gaps before adding workers. Complete the two-model comparison and record cleanup evidence.

## Week 2 — Durable run lifecycle

* Add Temporal workflow and activities, stable start IDs, heartbeats, bounded retry, and cancellation.
* Persist run/task state, findings, artifacts, and desktop leases.
* Add usage reservations, usage reconciliation, and a resource reaper.
* Exercise worker termination and replacement-desktop recovery early.

### Feature checklist

- [ ] W2-F01: Temporal workflow/activities with stable start IDs that prevent duplicate run starts.
- [ ] W2-F02: Activity heartbeats, bounded retries, cancellation, and timeouts.
- [ ] W2-F03: Persist run/task state, findings, artifact references, and desktop leases.
- [ ] W2-F04: Checkpoint completed visual steps and source findings; distinguish a proposed action from an executed action and avoid blindly replaying uncertain desktop effects.
- [ ] W2-F05: Reserve model usage before admission and reconcile actual usage afterward.
- [ ] W2-F06: Reap idle/orphaned desktops and expire viewer access with the desktop lease.
- [ ] W2-F07: Kill a worker mid-task, provision a replacement desktop, and resume from persisted progress; refresh observations rather than reuse stale screen state.
- [ ] W2-F08: Demonstrate cancellation and timeout cleanup, with no indefinitely running desktop; record failure-injection results.

Exit: stop a worker during a research task and recover from persisted progress. Cancellation and timeout leave no indefinitely running desktops.

## Week 3 — Real agent communication

* Add dynamic task DAG generation and validation, with at most three active desktops.
* Implement message schemas, transactional outbox, dispatcher, and deduplication.
* Add versioned proposals, conditional acceptance transactions, and structured objections.
* Permit bounded reassignment and follow-up tasks as findings arrive.

### Feature checklist

- [ ] W3-F01: Generate and validate a dynamic task DAG with at most three active isolated desktops.
- [ ] W3-F02: Define typed finding, handoff, proposal, objection, and revision messages with run/task identity and source provenance.
- [ ] W3-F03: Persist each outgoing message and transactional outbox row atomically.
- [ ] W3-F04: Dispatch messages with retries and deduplicate consumption; repeated delivery changes state once.
- [ ] W3-F05: Version shared proposals and accept updates conditionally; reject stale updates explicitly.
- [ ] W3-F06: Surface incompatible concurrent proposals as conflicts with structured objections and reevaluation.
- [ ] W3-F07: Bound reassignment/follow-up work by the run's usage, time, and desktop limits.
- [ ] W3-F08: Demonstrate one worker finding and handoff to another worker; record duplicate-delivery and conflict experiments.

Exit: workers exchange a finding and a handoff; duplicate delivery changes state once. Concurrent incompatible proposals produce an explicit conflict and reevaluation.

## Week 4 — Useful end-to-end experience

* Build prompt interpretation, missing-information clarification, and run commands.
* Add task status, message timeline, artifact access, and resumable SSE events.
* Complete the weekend-trip benchmark with provenance, budget/timing checks, and partial-result handling.
* Run a product-comparison task using the same runtime to check generality.

### Feature checklist

- [ ] W4-F01: Interpret user goals and ask for missing information before execution when needed.
- [ ] W4-F02: Connect dashboard submission to real runs; expose watch, redirect, cancel, and finish controls.
- [ ] W4-F03: Show each agent's real authenticated live desktop with task status; switch among at most three desktops and visibly show disconnection/replacement.
- [ ] W4-F04: Display proposed/completed/denied actions and message timeline without presenting proposed actions as executed ones.
- [ ] W4-F05: Serve authorized artifacts and sourced final results with usable provenance links.
- [ ] W4-F06: Resume SSE from an event cursor and restore run/event state after dashboard reconnect.
- [ ] W4-F07: Finish the weekend-trip benchmark with budget/timing checks, provenance, and useful partial results.
- [ ] W4-F08: Complete a product-comparison task through the same runtime and visual tools.
- [ ] W4-F09: Compare equivalent tasks against a single-agent baseline using the same budget; record when coordination helps or adds overhead.

Exit: a user can submit, watch, redirect, and finish a run. Reconnecting the dashboard preserves the run and event history.

## Week 5 — Security and failure evidence

* Add controlled malicious-page and malicious-message fixtures with synthetic secrets.
* Test cross-run access, stale proposals, duplicate messages, limits, cancellation, and recovery.
* Instrument distributed traces and summarize cost, latency, task success, recovery outcomes, and blocked actions.
* Implement 24-hour retention and user-requested deletion, including artifact access invalidation.

### Feature checklist

- [ ] W5-F01: Controlled malicious-page and message fixtures with synthetic secrets; include instructions visible in screenshots and prove external action checks still apply.
- [ ] W5-F02: Cross-run authorization checks for tools, messages, artifacts, and live-view sessions.
- [ ] W5-F03: Regression cases for stale proposals, duplicate delivery, limits, cancellation, and worker/desktop recovery.
- [ ] W5-F04: Distributed traces correlating model requests, proposed/admitted actions, messages, and lifecycle events without logging secrets.
- [ ] W5-F05: Versioned evaluation report covering task/citation success, cost, latency, recovery, and blocked actions with model/configuration and failure categories.
- [ ] W5-F06: Enforce 24-hour retention and user deletion for run content and stored screenshot/artifact data; invalidate associated access links and document provider/backups separately.
- [ ] W5-F07: Reproducible security/failure walkthrough and a threat model whose claims match observed evidence.

Exit: reproducible tests support each stated security and reliability claim. Document observed limitations and provider retention separately.

## Week 6 — Private beta and portfolio

* Package one-command local startup, environment documentation, and architecture diagrams.
* Choose a hosted configuration only after measuring its recurring cost; preserve local deployment if the budget cannot cover safe hosting.
* Invite a small tester group if hosting is viable; record bugs and measured runs.
* Record a short live-task demo and a separate failure/security walkthrough.
* Write a clear README and resume bullets backed by actual measurements.

### Feature checklist

- [ ] W6-F01: One-command local startup with documented prerequisites, environment setup, migrations, and cleanup.
- [ ] W6-F02: Current architecture diagrams, feature status, operational limits, and reproducible demo instructions.
- [ ] W6-F03: Measure recurring hosting/model/desktop costs; select safe hosting within budget or retain local deployment.
- [ ] W6-F04: If hosting is viable, provide invite-only access with run ownership and authenticated live views; otherwise document the local tester workflow.
- [ ] W6-F05: Observe a small tester group doing real tasks; record failures, feedback, and resulting fixes.
- [ ] W6-F06: Record a live visual research demo showing actual desktops, scrolling, collaboration, and cited results.
- [ ] W6-F07: Record a separate worker-recovery and security-boundary walkthrough.
- [ ] W6-F08: Publish reproducible evaluation results, technical write-up, and README/resume claims supported by measurements.

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
