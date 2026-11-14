# Decision 0001: Product positioning, clicking, browsing scope, and credentials

- Date: November 13, 2026.
- Status: accepted by the user (project owner); not yet implemented beyond Week 1.
- Recorded by: Claude, from a design discussion with the user.

## Context

The project's watchable desktop experience was inspired by **Opticon**
([Devpost](https://devpost.com/software/opticon)), a hackathon project the user
attributes to Jonathan Mo of Columbia. Opticon's write-up motivates the product
with agents that caused damage when given a person's own computer (an unwanted
$3k charge, a deleted production database) and names "prompt injection attacks,
data leaks, misplaced authority" as the problem. Its answer: one cloud VM (E2B)
per agent, an orchestrator splitting a prompt into parallel subtasks, a dashboard
of live desktops, a shared whiteboard, and recorded sessions. Agents can click,
type, and browse with full internet access. Its "what's next" includes agents
handing each other credentials, and better recovery when an agent goes down.

The user asked which market the visual design fits, whether to allow broad
browsing, whether to add clicking, and whether agents should receive credentials.

## Decision

1. **Positioning.** The same category as Opticon (delegating computer work to
   watchable agents on isolated cloud desktops), differentiated on **authority
   control and reliability**: "a team of AI agents you can watch, with hard limits
   on what they are allowed to do." A VM protects the user's laptop; it does not
   stop an agent with network access from leaking data or obeying a malicious page.
   The permission gateway, network limits, and durable runs address that gap.
2. **Clicking will be added**, as its own task after Week 1 exit, with its own
   authorization and evaluation case (as this plan already requires for new
   actions): clicks only inside the browser page area, checked by the gateway, and
   every resulting request still checked by the browser filter and E2B firewall.
   Clicking is preferred over model-typed URLs because the model can only follow
   links that already exist on a page, which closes the main channel for
   smuggling data out in a URL it composes.
3. **Broad public browsing comes later, not now.** Prerequisites: W1-3 proves
   private/link-local/metadata destinations are blocked (including IPv6,
   redirects, DNS); then navigation is limited to search results and links on
   visited pages (link provenance), never free-form model URLs. "Read-only" is not
   treated as safe: a GET request can carry data out in its URL.
4. **Agents never hold credentials.** No logins, purchases, or credentials in
   model context or screenshots for this release (as the architecture already
   states). If logins are needed later: the user signs in through live-desktop
   takeover, or scoped access (e.g. OAuth) is injected outside the model; risky
   actions need user approval; sessions end with the desktop.
5. **W1-6 scope stays narrow**: one permitted host (Wikipedia), scroll and finish
   only; stylesheets from permitted hosts are allowed so pages render as a person
   sees them.

## Consequences

- Placement confirmed by the user at review: W1X-F01 (clicking) and W1X-F02
  (broad public browsing) in the implementation plan, after Week 1 exit and before
  Week 3. W1X-F02 waits for W1-F10 network evidence; the user raised opening the
  web first and blocking later, and the sequencing trade-off was discussed.
- Use-case validation remains open. Candidates discussed (benefits navigator,
  usability/accessibility testing) did not resonate; the positioning above is the
  working direction.
- Visual agents are token-heavy (about 2.8k input tokens per full-size
  screenshot step on `qwen/qwen3.8-27b`); this affects parallel agents and the
  W1-4 cost comparison.
