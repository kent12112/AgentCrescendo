# E2B network preflight

The next milestone is a real desktop. Before connecting it to the model loop,
check its network behavior independently. A page can make requests without a
model tool call, so `authorize()` alone cannot enforce browser egress.

This check uses a separate E2B account and may consume paid resources or credits.
It creates one desktop with a 240-second lifetime (destroyed, not paused, on
expiry), runs fixed connection probes, and calls `kill()` in a `finally` block. It does not run a model or configure billing.

## Run

From the repository root, install the optional SDK into the existing venv.
`-m pip` uses that interpreter's installer; `-e` installs the project in editable
mode, and `[e2b]` selects its E2B dependencies. This changes the virtual environment:

```sh
.venv/bin/python -m pip install -e '.[e2b]'
```

Create an E2B API key in your account. This zsh command reads it without displaying
it or putting its value in command history. `export` makes it available to child
processes; it remains set only for the current shell session:

```zsh
read -s "E2B_API_KEY?Paste your E2B API key: "
export E2B_API_KEY
echo
```

Run the cloud probe. This command creates and destroys a remote desktop:

```sh
.venv/bin/python scripts/e2b_preflight.py
```

The sandbox is configured to deny outbound traffic except `en.wikipedia.org`,
and to require authentication for its public URLs. No Groq key is passed into it.
E2B automatically permits DNS resolver traffic when a domain allowlist is used;
this is a documented exception to a literal Wikipedia-only network claim.

Expected results:

| Probe | Expected `reachable` |
| --- | --- |
| Wikipedia HTTPS | `true` |
| Unlisted example.com HTTPS | `false` |
| Metadata IP TCP port 80 | May be `true`: sandbox-local MMDS exception |
| Private IP TCP port 80 | `false` |
| Public IPv6 `2606:4700:4700::1111` TCP 443 | `false` (added November 16, 2026) |
| Private IPv6 `fd00::1` TCP 80 | `false` (added November 16, 2026) |
| Wikipedia's IPv6 (AAAA) address TCP 443 | Either: informational |
| UDP DNS to `1.1.1.1` (not the default resolver) | `false` |
| `en.wiktionary.org` TLS (unlisted name, same IPs as Wikipedia) | `false` |
| Allowed TLS name sent to example.com's IP, cert checked | Wikipedia's server or blocked; any other server fails |
| `Host: en.wikipedia.org` over HTTP to example.com's IP | Same rule |
| Allowed TLS name sent to private `10.0.0.1` | Same rule |
| `/wiki/wikt:Boston` redirect: connect to its off-host target | `false` |
| Lookup of an unlisted name; UDP DNS and TCP 443 to `8.8.8.8` | Informational: E2B's DNS exception |
| Allowed TLS name, inner `Host: en.wiktionary.org` (domain fronting) | Informational: a known limit |

Added November 16, 2026 to finish W1-F10. The "same rule" rows report an
`outcome` instead of `reachable`: `allowed_server` (certificate valid for
Wikipedia, so the firewall picked the IP by name), `other_server` (a different
server answered: failure), `blocked`, or `tls_alert` (ambiguous: failure).

## Browser-originated traffic

The probes above are a plain program in the guest. A page also makes requests
on its own, without a tool call. Check those with the real browser and filter:

```sh
.venv/bin/python scripts/e2b_network_browser_check.py
```

This creates one metered desktop (180-second lifetime), no model calls. It loads
a page whose stylesheets, images, iframe, and prefetch point at example.com,
plain HTTP, `10.0.0.1`, and `169.254.169.254`; a meta refresh to example.com;
and a live navigation to `/wiki/wikt:Boston`, which Wikipedia redirects to
Wiktionary. Every forbidden item must fail to load, an allowed Wikipedia
stylesheet must load, and the redirect hop must be blocked. Before a paid run,
`.venv/bin/python scripts/smoke_browser_subrequests.py` runs the same checks in
local Edge with the real filter and locally supplied responses (no internet).

Why IPv6: `deny_out` is `0.0.0.0/0`, an IPv4 range. Nothing yet shows whether
IPv6 traffic is denied, has no route at all, or passes. TCP probes now record an
`error` name: `ENETUNREACH` means no IPv6 route, `TimeoutError` usually means
dropped packets, `ECONNREFUSED` means something answered. All count as blocked,
but they mean different things, so record which one appears.

`evaluate_preflight()` holds the pass/fail rules (unit tested); the script prints
raw results first, then notes, then exits nonzero if any rule failed. A missing or
malformed probe result is a failure, not a pass.

The IP probes open TCP connections only; they do not request metadata or read
credentials. An HTTP error such as 403 still counts as reachable: the network
allowed the request even if the server rejected it.

## Metadata exception: investigation result

The first live run returned Wikipedia HTTP 200, unlisted example.com unreachable,
metadata TCP reachable, and private TCP unreachable. Our original script treated
metadata reachability as an egress failure; that interpretation was too broad.

E2B contributors explain that per-VM Firecracker MMDS handles this address outside
the filtered egress path. They describe sandbox metadata rather than host cloud
credentials, and no supported workload restriction that preserves initialization.
See the [E2B response](https://github.com/e2b-dev/runtime/issues/3625) and
[runtime source](https://github.com/e2b-dev/runtime/blob/main/packages/envd/internal/host/mmds.go).

Our TCP test does not identify the service; the explanation comes from upstream,
not a local HTTP inspection. Metadata reachability is now informational rather
than an external-egress failure. This does not establish complete isolation.

## Interpretation and remaining work

A failed connection can mean blocked traffic, no listener, DNS failure, or a
routing problem. Loopback inside the guest is the guest itself, not your Mac's backend.

### Completion results (November 16, 2026)

Two live preflight runs and two live browser-check runs, all passing, identical
results each time. Run by Claude in the VS Code session; no model calls.

Network layer (preflight):

- **The firewall routes allowed names by name.** TLS naming `en.wikipedia.org`
  sent to example.com's IP got a valid Wikipedia certificate; the same over
  HTTP got Wikipedia's `301`. The guest's chosen IP was ignored. This is also the
  DNS-rebinding answer: a lying DNS reply for an allowed name still leads to the
  real Wikipedia, not to the address in the reply.
- **Private ranges are dropped before name matching.** The allowed name sent to
  `10.0.0.1` timed out (as did plain TCP there).
- **Shared IPs do not widen the allowlist.** `en.wiktionary.org` (same Wikimedia
  servers) was closed during the TLS handshake (`SSLEOFError`), as was example.com.
- **Redirects are judged per connection.** `/wiki/wikt:Boston` returned `301` to
  `en.wiktionary.org`; connecting there was closed the same way.
- **Only the default resolver is open.** UDP DNS to `1.1.1.1` timed out.

Documented exceptions (recorded as notes, not failures):

- **`8.8.8.8` accepts all traffic**, including TCP 443, not just DNS. E2B's SDK
  says so for its default `dns_servers`. Every name the guest looks up, allowed
  or not, is sent there. This is an outbound channel to Google's resolver.
- **Domain fronting works at the network layer.** TLS naming Wikipedia with an
  encrypted `Host: en.wiktionary.org` was served Wiktionary. The firewall sees
  only the TLS name; sites sharing an allowed host's servers are reachable to any
  program that composes its own requests.
- IPv6: no guest route (unchanged). Metadata IP: MMDS exception (unchanged).

Browser layer (real Chrome, real request filter):

- Allowed Wikipedia stylesheet loaded. Stylesheet, image, and iframe on
  example.com; image on Wikipedia (images are not an allowed type); plain-HTTP,
  `10.0.0.1`, and metadata-IP images were all failed by our filter. The meta
  refresh and the live Wiktionary redirect hop were blocked; the page ended on
  Chrome's error page.
- `<link rel=prefetch>` never reached the filter: on E2B Chrome did not issue
  it; in local Edge it failed outside the filter. `preconnect` and
  `dns-prefetch` cannot be observed by the filter at all. A page can therefore
  cause DNS lookups of names it chooses, via `8.8.8.8`, and connection attempts
  that only the firewall stops.

### Narrowed supported behavior

The two exceptions require a program that composes its own traffic. The agent
has no such tool: model tools are `navigate`, `click`, `click_link`, `scroll`,
`search_page`, and `finish`; guest commands are fixed host-side programs (start
Chrome, debugger relay, readiness waits). Chrome sends the same name in TLS and
in `Host`, and every request it exposes passes the filter. So, supported:

- One E2B desktop, one browser, an exact-host allowlist, no code execution in
  the guest by the model, no credentials in the guest.
- Accepted residual risk: a hostile page can leak what it already contains
  through DNS lookups (`dns-prefetch`) to the default resolver. It cannot read
  our secrets, because none are in the guest.

Not supported until revisited: any tool that runs model-chosen code or shell
commands in the guest; secrets inside the guest. Either would turn the
`8.8.8.8` and domain-fronting paths into real exfiltration routes. Hardening
options, unverified: `dns_servers: []` plus `/etc/hosts` entries for allowed
hosts, or a self-run resolver; `--dns-prefetch-disable` for Chrome.

What this does not prove: behavior under future E2B or Chrome changes (rerun
both checks after upgrades); exhaustive browser request types (WebSocket, fetch,
and service workers are off because JavaScript is disabled); live-view access,
which is covered in [live viewer diagnosis](learning/10-live-desktop-view.md).

Sources: [E2B network controls](https://docs.e2b.dev/network/internet-access),
[Desktop SDK](https://github.com/e2b-dev/desktop); SDK docstrings for
`SandboxNetworkOpts.dns_servers` (e2b 2.63.0).

## Learning record

Decision: test the cloud boundary independently before giving the model a browser.
Prediction: the allowed public page is reachable; the other probes cannot connect.
Offline result: package tests pass, including restricted creation and cleanup on
command/output failures. Live result: user-provided output recorded above; metadata
exception investigated against upstream source and contributor responses. No second
cloud run performed.
Tradeoff: a small diagnostic step delays live browsing but makes network failures
easier to distinguish from model and browser failures.

IPv6 addition (November 16, 2026). Decision: measure IPv6 under the existing
IPv4-only deny rule before changing configuration, so the result shows today's
real boundary. Prediction: both IPv6 literals unreachable, most likely
`ENETUNREACH` (no IPv6 route). If either connects, browsing stays disabled and
the next step is testing `"::/0"` in `deny_out`. Offline result: 18 preflight tests
pass; the probe helper returned `ECONNREFUSED` for closed local IPv4/IPv6 ports.
Live result (user-run, November 16, 2026, one run): passed. Wikipedia HTTP 200;
example.com unreachable; metadata TCP reachable (MMDS note); private IPv4
`TimeoutError`; public IPv6, private IPv6, and Wikipedia over IPv6 all
`ENETUNREACH`. Interpretation: the guest had no IPv6 route at all, so IPv6 was not
an egress path in this run. That is absence of a route, not a firewall rule: if
E2B later enables guest IPv6, the IPv4-only `0.0.0.0/0` deny may not cover it.
Rerun this probe after SDK or provider changes; whether `deny_out` accepts
`"::/0"` is unverified. The private IPv4 timeout (not refusal) is consistent with
dropped packets but does not by itself prove firewall enforcement.

Completion (November 16, 2026). Decision: test the firewall's name matching
directly (allowed name, other IP) instead of standing up hostile DNS; it answers
the rebinding question with the same evidence. Prediction: either blocked or
routed to Wikipedia; uncertain which. Offline: 446 Python tests, plus a local Edge
run of the browser checks. Its first version failed a correct block because Chrome's
error page was read as a foreign host; fixed. The first live preflight
mislabeled TLS closes as `ENOEXEC` (an OpenSSL code read as an OS errno); fixed
and rerun. Live result: two preflight and two browser runs passed. Surprise:
`8.8.8.8` is open on all ports, not only DNS; domain fronting succeeds. Both are
outside the model's reach today and recorded as explicit narrowing.

## Public-web mode (W1X-F02)

Broad browsing has no host allowlist. E2B denies `PRIVATE_NETWORKS` (in
`crescendo_security.policy`) and allows everything else; see
[decision 0004](decisions/0004-public-web-mode.md). Check it with:

```sh
.venv/bin/python scripts/e2b_preflight.py --public
.venv/bin/python scripts/e2b_network_browser_check.py --public
```

The preflight adds a **positive control**. Private targets usually have no
listener, so "no connection" there proves nothing on its own. The public address
`1.1.1.1` is added to the deny list and must give no answer, while its twin
`1.0.0.1` must answer. Only server-proven answers count: a verified TLS handshake
for `one.one.one.one`, or a reply to a DNS question.

Results, November 16, 2026, two live runs of each check, identical:

| Probe | Result |
| --- | --- |
| example.com, Wikipedia, boston.gov over HTTPS | HTTP 200 |
| Canary `1.1.1.1` (denied) | No TLS (`SSLEOFError`), no DNS answer |
| Twin `1.0.0.1` (not denied) | TLS verified, DNS answered |
| `10.0.0.1`, `172.16.0.1`, `192.168.0.1`, `100.64.0.1` TCP 80 | Timed out |
| `10.0.0.1.sslip.io`, `192.168.0.1.sslip.io` | Resolved to the private address; connect timed out |
| Guest gateway `169.254.0.22` TCP 80 | Timed out |
| Metadata `169.254.169.254` TCP 80 | Connected (MMDS exception, unchanged) |
| IPv6 | No route (unchanged) |

Browser check (`--public`): Wikipedia's stylesheet and the boston.gov page loaded.
Stylesheets on the two rebinding names passed the filter, because they are
public-looking names, and never got a response within 25 seconds. IP literals,
metadata, `localhost`, and an image were refused by the filter.

Mistakes and surprises, kept as evidence:

- E2B rejected `0.0.0.0/8` (`400: invalid denied CIDR`); no desktop was created.
- The first canary probe used a plain TCP connect to port 443, which
  "connected" even though the address was denied: E2B's proxy accepts first and
  judges afterwards. A two-configuration diagnostic with TLS and DNS proofs
  showed the deny list was enforced all along. The probe was fixed; the judge
  test keeps a reachable canary as a failure.
- Requests the firewall drops hang rather than fail, so the browser check waits
  a fixed time and records them as `pending`.
