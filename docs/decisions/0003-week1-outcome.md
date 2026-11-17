# Decision: Week 1 outcome and what carries forward

Date: November 16, 2026. Scope: Week 1, "one useful, constrained desktop agent"
([plan](../implementation-plan.md#week-1--one-useful-constrained-desktop-agent)).

## Context

Week 1 had to show one agent doing visual research on a public page inside an
isolated desktop, watched live by the user, behind permissions enforced outside
the model. Evidence is in [status](../status.md),
[annotated traces](../week1-traces.md), and the linked handoffs.

Exit criteria, as of this date:

| Criterion | State | Evidence |
| --- | --- | --- |
| Visual research with a cited result while the user watches | Met | W1-F09, trace A |
| Permitted browsing works; private/backend destinations blocked | Met, with narrowing | W1-F10, [preflight](../e2b-preflight.md) |
| E2B networking and live view fit the security design | Met, with narrowing | W1-F08, W1-F10 |
| Cleanup evidence | Met | W1-F11, [termination](../e2b-termination.md) |
| Two-model comparison | **Not met; deferred by the user** | W1-4 in status |

## Decisions

1. **The agent sees screenshots and acts through a fixed tool list.** The tools
   are `scroll`, `click`/`click_link`, `navigate`, `search_page` and `finish`.
   The model never runs code in the desktop. This rule is what makes the
   network exceptions below acceptable.
2. **Links are chosen by browser-measured ID, not by pixels**
   ([decision 0002](0002-visible-link-grounding.md)). Trace B shows why: the
   model knew the target but missed by about 150 px. Screenshot-only pixel
   grounding is unsolved and is not claimed.
3. **Two enforcement layers, each judged on its own evidence.** Our request
   filter inside Chrome sees full URLs. E2B's firewall sees only addresses and
   TLS names, routes allowed names by name, and drops private ranges.
4. **Known network exceptions are accepted, narrowed, and written down rather
   than hidden.** The DNS server `8.8.8.8` is open on all ports, and domain
   fronting works at the network layer. Both need self-built traffic, which no
   tool provides. Adding a code-execution tool, or any secret in the desktop,
   reopens this decision.
5. **Desktops are destroyed, never paused.** The adapter kills the desktop in
   cleanup, and E2B's lifetime timer is set to kill as a fallback.
6. **Provider failures are a separate outcome from model failures.** Timeouts,
   rate limits and server errors get bounded retries and distinct statuses.
   Trace C failed after the model had already done the right thing.
7. **The dashboard stays draft-only for now.** Agents run from CLI scripts.
   Connecting the dashboard to execution is Week 4 work and needs durable runs
   (Week 2) first.

## Consequences

- Week 2 (durable run lifecycle) can start on this single-agent base. The
  network and live-view boundaries it depends on are measured, not assumed.
- The model question is open. Every live result so far is from
  `qwen/qwen3.8-27b`, the only vision model on the configured Groq account.
  Claims about accuracy or cost apply to that model only. Choosing a second
  candidate, either on the text loop or from another vision provider, is the
  user's decision, and Week 1 is not fully closed until it is made.
- Evidence is from a handful of live runs per feature: enough to show
  behavior, not to measure reliability. Repeated runs belong with the model
  comparison.
- Broad public browsing (W1X-F02) cannot use a name allowlist. It needs a
  "public allowed, private denied" firewall setup, a live check that allow and
  deny rules combine as expected, and a real DNS-rebinding test.
- Rerun `scripts/e2b_preflight.py` and `scripts/e2b_network_browser_check.py`
  after any E2B, Chrome, or SDK upgrade.
