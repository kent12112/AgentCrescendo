# Decision: public-web mode for broad browsing

Date: November 16, 2026. Scope: W1X-F02 ([plan](../implementation-plan.md)).

> Movement rule 3 (model `navigate` refused) was replaced on November 17, 2026
> by [decision 0005](0005-open-browsing.md): open browsing with `navigate` and
> `type_text`. Network and request-filter rules here still apply.

## Context

Week 1 used an exact-host allowlist at two layers: our request filter in Chrome,
and E2B's firewall routing allowed names by name. Broad browsing cannot list
hosts in advance, so a name allowlist no longer works at either layer. The
threats that matter once any public site is allowed:

- private, link-local, metadata, and backend addresses, reached directly or
  through a public name that resolves to one (DNS rebinding);
- a model encoding data into URLs it composes, sent to any site;
- pages leading the browser somewhere unsafe on their own.

## Decision

A grant can set `public_web=True`. In that mode:

1. **Network layer (enforcement).** E2B gets no allowlist and denies
   `PRIVATE_NETWORKS`: RFC 1918, carrier-grade NAT, loopback, link-local and
   metadata, and IETF special ranges. Only this layer can stop a rebinding name,
   because the filter never learns which address a name resolves to.
2. **Request filter (defense in depth).** `authorize_destination()` allows any
   public site name over HTTPS without a port or credentials. It refuses every IP
   address, including browser IPv4 spellings such as `2130706433` and `0x7f.1`,
   along with single-label and conventional internal names (`localhost`,
   `.local`, `.internal`, ...). The resource-type rule (documents and
   stylesheets only) is unchanged. The filter no longer depends on the model's
   `navigate` tool.
3. **Movement.** The model's `navigate` is always refused, even if granted by
   mistake. The host opens the start page with `open_start_page()`. After that
   the model moves only by `click_link` on links that exist on the page.
4. Allowlist mode is unchanged and remains the default.

## Evidence

Two live runs each, November 16, 2026; see [preflight](../e2b-preflight.md#public-web-mode-w1x-f02).

- `scripts/e2b_preflight.py --public`. A denied public canary (`1.1.1.1`) gave
  no TLS or DNS answer while its twin `1.0.0.1` answered, so the deny list is
  enforced. `10.0.0.1.sslip.io` and `192.168.0.1.sslip.io` resolved to private
  addresses and could not connect. Public sites connected.
- `scripts/e2b_network_browser_check.py --public`. Chrome's requests to
  rebinding names passed the filter and never got a response. IP literals,
  metadata, `localhost`, and images were refused by the filter.
- `scripts/e2b_public_browse_demo.py`. The model reached `www.boston.gov` from
  Wikipedia with one `click_link` and named it, with no `navigate` tool and no
  host list.

## Consequences

- **Plain TCP connect is not evidence on E2B.** Its proxy accepts every TCP
  connection on port 443 itself. The first canary attempt "connected" and was
  wrong. Reachability claims need an answer only the real server could give.
- E2B rejects `0.0.0.0/8` in `deny_out`. It is omitted; Linux treats `0.x` as
  the local machine.
- The metadata exception (E2B's sandbox-local MMDS) remains. IPv6 has no guest
  route; if E2B adds one, IPv6 private ranges need denying too.
- Firewall-dropped requests hang instead of failing, so pages that reference
  private names load slowly. Checks must not wait for the page's `load` event.
- **Most public sites are only partly readable.** The filter blocks fonts,
  scripts, and images. boston.gov rendered with invisible text because its web
  fonts were blocked. Allowing fonts (and perhaps images) is a separate,
  explicit decision. Fonts would add no new destinations, since stylesheets
  can already reach any public host.
- Data in clicks is still possible: a hostile page can offer links whose
  URLs encode what the page shows. The agent holds no credentials, so this
  can only leak page content and the task goal.
- Any tool that types text (search boxes, forms) is outside this decision and
  needs its own authorization and evaluation case.
