# Decision: open browsing (model navigate and typing) in public-web mode

Date: November 17, 2026. Scope: W1X-F03 ([plan](../implementation-plan.md)).
Changes movement rule 3 of [decision 0004](0004-public-web-mode.md); its
network and request-filter rules are unchanged.

## Context

Decision 0004 refused the model's `navigate` in public-web mode, so it could
move only by clicking links on the current page. It could not open a site it
already knew, go back to an earlier page, or use a search box. The user judged
this too limiting for a useful product.

The rule protected against one thing: a model, perhaps steered by a hostile
page, writing data into a URL or a search box and sending it to a site. 0004
already accepted that the same data can leave through a hostile page's links,
and the agent holds no credentials. What can leak is page content and the
task goal.

Alternatives considered:

- **URL provenance**: allow only URLs the host has seen (task text, search
  results, links shown). This blocks model-written text from going out, but
  still can't type into a site's own search box.
- **Bare domain names only**: rejected; a subdomain can carry data.
- **Open browsing**: chosen, as a single mode. The user asked for only this.

## Decision

In public-web mode:

1. **`navigate` allowed to any public site.** The gateway applies
   `authorize_destination()`, the same check the request filter applies to
   every page request (HTTPS, a public name, no IP, port, or credentials).
   The E2B deny list of private ranges stays. The tool must still be granted.
2. **`type_text(target_id, text, submit)`.** Text fields are listed with links
   in `visible_links` as `kind: "field"`: text, search, email, url, tel and
   number inputs, and textareas. Password, hidden, disabled, read-only,
   framed, and covered fields are never listed or typed into. Checks, in order:
   - gateway: one line of 1–200 printable characters (no newline, tab, or
     control character), boolean `submit`, point inside the page area;
   - adapter: the element under the point is a permitted field, and its form
     does not open a new tab;
   - real pointer click on the field;
   - this tab really has keyboard focus on that field. Playwright's focus
     emulation is turned off first, because with it on a page always claims
     focus (local Edge check);
   - Ctrl+A, then the text, then a focus re-check before Enter.
3. **Browser controls stay off-limits.** No tool can reach the address bar or
   tabs. Clicks and typing are confined to the page area (y ≥ 114), and keys
   are sent only after the focus check. The only keys ever sent are Ctrl+A
   and Enter.
4. Allowlist mode is unchanged and remains the default.

What makes typing bounded: page scripts are disabled, and the filter passes
only GET requests. Typed text sits in the page until a form is submitted, then
leaves only as the query of a GET URL that passes the same destination check.
POST forms (logins, comments, purchases) are blocked.

## Accepted risk

**Model-written text can now reach any public site**, through a URL or a
search submission. A prompt-injected page could get the task goal or page
content sent to a site it controls. This is acceptable while agents hold no
credentials and no personal data. Revisit it before any task carries user
data or signs in. That is the point where URL provenance (above) or a
confirmation step becomes necessary.

## Evidence

Local, November 17, 2026: 567 Python tests passed.
`scripts/smoke_type_text_fields.py` ran the real field JavaScript in local
Edge with scripts disabled: listing, resolving, refusals, and the
focus-emulation behaviour. The existing local smoke checks still pass.

Not yet observed live:

- that real E2B keyboard focus is reported after a real click;
- that Wikipedia's search form submits without scripts;
- that the model uses the tools.

`scripts/e2b_open_browse_demo.py` is the live check.

## Consequences

- Sites whose search is built with JavaScript won't work, since scripts stay
  blocked. Plain HTML forms do (Wikipedia, DuckDuckGo's HTML version).
  Allowing scripts would be a far larger change than this one.
- A mistyped or unreachable model URL becomes an observation ("did not load
  (net::ERR_…)") through `navigate_and_report()`, not a crash. Plain
  `navigate()` keeps raising for other callers.
- If the focus check is wrong on E2B, it fails closed: nothing is typed.
