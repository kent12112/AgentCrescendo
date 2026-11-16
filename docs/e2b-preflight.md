# E2B network preflight

The next milestone is a real desktop. Before connecting it to the model loop,
check its network behavior independently. A page can make requests without a
model tool call, so `authorize()` alone cannot enforce browser egress.

This check uses a separate E2B account and may consume paid resources or credits.
It creates one desktop with a 120-second lifetime, runs fixed connection probes,
and calls `kill()` in a `finally` block. It does not run a model or configure billing.

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
routing problem. These probes are preliminary evidence, not proof of firewall
enforcement. Loopback inside the guest is the guest itself, not your Mac's backend.

Next checks need a controlled reachable destination, redirects, DNS rebinding,
browser subrequests, and authenticated live-view access. IPv6: one live run
(November 16, 2026) found no guest IPv6 route; see the learning record below. E2B documents that
allow rules take precedence over deny rules; domain resolution and shared IPs
need verification before claiming exact hostname isolation at the network layer.
Only after reviewing these results should we wire a browser into `Desktop`.

Sources: [E2B network controls](https://docs.e2b.dev/network/internet-access),
[Desktop SDK](https://github.com/e2b-dev/desktop).

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
