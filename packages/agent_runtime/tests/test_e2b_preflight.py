# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import runpy: use this module through its namespace.
import runpy
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.e2b_preflight: the probe text, the rule groups, the evaluator, and
# the runner under test.
from crescendo_agent.e2b_preflight import (
    INFORMATIONAL, MUST_BLOCK, MUST_REACH, NAME_BOUND, PROBE, evaluate_preflight, run_preflight,
)


# Define expected_results with no parameters.
def expected_results():
    """Return a fresh result set that matches the expected network boundary."""
    # Return a new dictionary: Wikipedia reachable, every blocked probe unreachable, metadata
    # reachable (the documented MMDS exception), and Wikipedia over IPv6 unreachable.
    return {
        # Include allowed_wikipedia, reachable, http_status in this dictionary.
        "allowed_wikipedia": {"reachable": True, "http_status": 200},
        # Include unlisted_example, reachable in this dictionary.
        "unlisted_example": {"reachable": False},
        # Include metadata_tcp, reachable in this dictionary.
        "metadata_tcp": {"reachable": True},
        # Include private_tcp, reachable, error in this dictionary.
        "private_tcp": {"reachable": False, "error": "TimeoutError"},
        # Include public_ipv6_tcp, reachable, error in this dictionary.
        "public_ipv6_tcp": {"reachable": False, "error": "ENETUNREACH"},
        # Include private_ipv6_tcp, reachable, error in this dictionary.
        "private_ipv6_tcp": {"reachable": False, "error": "ENETUNREACH"},
        # Include wikipedia_ipv6_tcp, reachable, error in this dictionary.
        "wikipedia_ipv6_tcp": {"reachable": False, "error": "ENETUNREACH"},
        "dns_lookup_unlisted": {"resolved": True},
        "dns_udp_default_resolver": {"reachable": True},
        "dns_udp_other_resolver": {"reachable": False, "error": "TimeoutError"},
        "default_resolver_tcp443": {"reachable": True},
        "sni_to_unlisted_ip": {"outcome": "allowed_server"},
        "host_header_to_unlisted_ip": {"outcome": "blocked", "error": "ECONNRESET"},
        "sni_to_private_ip": {"outcome": "allowed_server"},
        "shared_ip_unlisted_name": {"reachable": False, "error": "ECONNRESET"},
        "domain_fronting": {"reachable": True, "http_status": 200, "served_other_site": True},
        "offhost_redirect": {"http_status": 301, "location_host": "en.wiktionary.org",
                             "reachable": False, "error": "ECONNRESET"},
    }


# Define test_network_is_restricted_from_creation_and_desktop_is_destroyed with no parameters.
def test_network_is_restricted_from_creation_and_desktop_is_destroyed():
    # Set factory to Mock().
    factory = Mock()
    # Set sandbox to factory.create.return_value.
    sandbox = factory.create.return_value
    # Set expected to {'allowed_wikipedia': {'reachable': True}}.
    expected = {"allowed_wikipedia": {"reachable": True}}
    # Set sandbox.commands.run.return_value.stdout to json.dumps(expected).
    sandbox.commands.run.return_value.stdout = json.dumps(expected)

    # Assert that run_preflight(sandbox_type=factory) equals expected. If false, this check fails
    # with AssertionError.
    assert run_preflight(sandbox_type=factory) == expected

    # Call factory.create.assert_called_once_with with no arguments.
    factory.create.assert_called_once_with(
        # Set timeout to 240 seconds.
        timeout=240,
        # Pass keyword network = a new dictionary with keys 'deny_out', 'allow_out',
        # 'allow_public_traffic'.
        network={"deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
                 # Include allow_public_traffic in this dictionary.
                 "allow_public_traffic": False},
        # Destroy, not pause, if the lifetime runs out.
        lifecycle={"on_timeout": "kill"},
    )
    # Call sandbox.kill.assert_called_once_with with no arguments.
    sandbox.kill.assert_called_once_with()
    # Assert that the remote command may run for 170 seconds, inside the 240-second lifetime.
    assert sandbox.commands.run.call_args.kwargs["timeout"] == 170 < 240


# Define test_probe_compiles_and_emits_every_judged_name with no parameters.
def test_probe_compiles_and_emits_every_judged_name():
    # Compile the remote source locally: a syntax error would otherwise appear only in a paid run.
    compile(PROBE, "<e2b preflight probe>", "exec")
    # Check every name the evaluator judges.
    for name in MUST_REACH + MUST_BLOCK + INFORMATIONAL + NAME_BOUND + ("dns_lookup_unlisted", "offhost_redirect"):
        # Assert that the probe writes a result under exactly that quoted name.
        assert f'"{name}"' in PROBE


# Define test_expected_boundary_passes_with_notes_only with no parameters.
def test_expected_boundary_passes_with_notes_only():
    # Set verdict to evaluate_preflight(expected_results()).
    verdict = evaluate_preflight(expected_results())
    # Assert that the verdict passed with no failures.
    assert verdict.passed and verdict.failures == ()
    # Assert that the metadata exception is reported as a note, not a failure.
    assert any(note.startswith("metadata_tcp accepted") for note in verdict.notes)
    # Assert that the IPv6 Wikipedia result is a note carrying its error name.
    assert any("wikipedia_ipv6_tcp not reachable (ENETUNREACH)" in note for note in verdict.notes)


# Run this test once per probe that must stay blocked.
@pytest.mark.parametrize("name", MUST_BLOCK)
# Define test_any_reachable_blocked_destination_fails with parameters name.
def test_any_reachable_blocked_destination_fails(name):
    # Set results to the expected set.
    results = expected_results()
    # Set results[name] to reachable, as if the firewall let it through.
    results[name] = {"reachable": True}
    # Set verdict to evaluate_preflight(results).
    verdict = evaluate_preflight(results)
    # Assert that the verdict failed with exactly one failure naming that probe.
    assert not verdict.passed
    # Assert that the single failure names the probe and says it was a disallowed destination.
    assert verdict.failures == (f"{name}: a disallowed destination was reachable; do not enable browsing.",)


# Define test_unreachable_allowed_destination_fails with no parameters.
def test_unreachable_allowed_destination_fails():
    # Set results to the expected set.
    results = expected_results()
    # Set results['allowed_wikipedia'] to unreachable.
    results["allowed_wikipedia"] = {"reachable": False}
    # Assert that the only failure says permitted browsing is not verified.
    assert evaluate_preflight(results).failures == (
        "allowed_wikipedia: unreachable; permitted browsing is not verified.",
    )


# Run this test once per broken entry: missing, not a dict, a string flag, and a 1 instead of True.
@pytest.mark.parametrize("broken", [None, "reachable", {"reachable": "yes"}, {"reachable": 1}, {}])
# Define test_missing_or_malformed_result_fails_closed with parameters broken.
def test_missing_or_malformed_result_fails_closed(broken):
    # Set results to the expected set.
    results = expected_results()
    # Check whether this case removes the entry entirely.
    if broken is None:
        # Delete the public IPv6 result.
        del results["public_ipv6_tcp"]
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Replace the public IPv6 result with the malformed value.
        results["public_ipv6_tcp"] = broken
    # Set verdict to evaluate_preflight(results).
    verdict = evaluate_preflight(results)
    # Assert that an unreadable blocked probe is a failure, never a silent pass.
    assert verdict.failures == ("public_ipv6_tcp: missing or malformed result; the evidence is incomplete.",)


# Define test_wikipedia_over_ipv6_is_informational_either_way with no parameters.
def test_wikipedia_over_ipv6_is_informational_either_way():
    # Set results to the expected set.
    results = expected_results()
    # Set results['wikipedia_ipv6_tcp'] to reachable.
    results["wikipedia_ipv6_tcp"] = {"reachable": True}
    # Set verdict to evaluate_preflight(results).
    verdict = evaluate_preflight(results)
    # Assert that it still passes and the result is recorded as a note.
    assert verdict.passed
    # Assert that the note says the allowed host was reachable over IPv6.
    assert "wikipedia_ipv6_tcp accepted: the allowed host was reachable over IPv6." in verdict.notes


# Run this test once per case: the expected boundary, and a reachable public IPv6 address.
@pytest.mark.parametrize("ipv6_reachable", [False, True])
# Define test_cli_exits_nonzero_only_when_a_rule_fails with parameters monkeypatch, capsys,
# ipv6_reachable.
def test_cli_exits_nonzero_only_when_a_rule_fails(monkeypatch, capsys, ipv6_reachable):
    # Call monkeypatch.setenv with 'E2B_API_KEY', 'offline-test'.
    monkeypatch.setenv("E2B_API_KEY", "offline-test")
    # Set results to the expected set.
    results = expected_results()
    # Set results['public_ipv6_tcp']['reachable'] to ipv6_reachable.
    results["public_ipv6_tcp"]["reachable"] = ipv6_reachable
    # Replace the cloud call with a function returning these results.
    monkeypatch.setattr("crescendo_agent.e2b_preflight.run_preflight", lambda: results)
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_preflight.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_preflight.py"
    # Check whether ipv6_reachable.
    if ipv6_reachable:
        # Use pytest.raises(SystemExit, match='public_ipv6_tcp: a disallowed destination'); leave
        # the context and run its cleanup when this block ends.
        with pytest.raises(SystemExit, match="public_ipv6_tcp: a disallowed destination"):
            # Call runpy.run_path with script converted to a string.
            runpy.run_path(str(script), run_name="__main__")
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Call runpy.run_path with script converted to a string.
        runpy.run_path(str(script), run_name="__main__")
        # Assert that the success line was printed.
        assert "External probes matched expectations" in capsys.readouterr().out


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("failure", [RuntimeError("command failed"), None])
# Define test_cleanup_runs_when_command_or_output_fails with parameters failure.
def test_cleanup_runs_when_command_or_output_fails(failure):
    # Set factory to Mock().
    factory = Mock()
    # Set sandbox to factory.create.return_value.
    sandbox = factory.create.return_value
    # Check whether failure is not None.
    if failure is not None:
        # Set sandbox.commands.run.side_effect to failure.
        sandbox.commands.run.side_effect = failure
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Set sandbox.commands.run.return_value.stdout to 'not JSON'.
        sandbox.commands.run.return_value.stdout = "not JSON"
    # Use pytest.raises((RuntimeError, ValueError)); leave the context and run its cleanup when this
    # block ends.
    with pytest.raises((RuntimeError, ValueError)):
        # Call run_preflight with no arguments.
        run_preflight(sandbox_type=factory)
    # Call sandbox.kill.assert_called_once_with with no arguments.
    sandbox.kill.assert_called_once_with()


# ---------------------------------------------------------------------------
# Name-bound probes, DNS notes, and the redirect rule (W1-F10 completion).
# ---------------------------------------------------------------------------

# Run once per probe that presents the allowed name to another IP.
@pytest.mark.parametrize("name", NAME_BOUND)
def test_allowed_name_reaching_another_server_fails(name):
    # "other_server" means the firewall forwarded to the IP the guest chose.
    results = expected_results()
    results[name] = {"outcome": "other_server", "error": "SSLCertVerificationError"}
    verdict = evaluate_preflight(results)
    assert not verdict.passed
    assert verdict.failures == (f"{name}: the allowed name reached a different server; the allowlist "
                                "does not constrain the destination IP. Do not enable browsing.",)


# Ambiguous or missing outcomes must never count as a pass.
@pytest.mark.parametrize("outcome", ["tls_alert", "not_run", None, "reachable"])
def test_ambiguous_name_bound_outcome_fails_closed(outcome):
    results = expected_results()
    results["sni_to_unlisted_ip"] = {"outcome": outcome} if outcome else {}
    verdict = evaluate_preflight(results)
    assert verdict.failures == (f"sni_to_unlisted_ip: outcome {outcome!r} is missing or ambiguous; "
                                "the evidence is incomplete.",)


def test_dns_and_fronting_exceptions_are_notes_not_failures():
    # Known, documented gaps are reported, but do not fail the run.
    verdict = evaluate_preflight(expected_results())
    assert verdict.passed
    joined = "\n".join(verdict.notes)
    for prefix in ("dns_lookup_unlisted resolved", "dns_udp_default_resolver accepted",
                   "default_resolver_tcp443 accepted", "domain_fronting served another site",
                   "sni_to_unlisted_ip: routed to the real allowed server",
                   "offhost_redirect: redirect to en.wiktionary.org was not reachable (ECONNRESET)"):
        assert prefix in joined


def test_reachable_offhost_redirect_fails():
    results = expected_results()
    results["offhost_redirect"]["reachable"] = True
    assert evaluate_preflight(results).failures == (
        "offhost_redirect: redirect destination en.wiktionary.org was reachable; do not enable browsing.",)


@pytest.mark.parametrize("entry", [None, {}, {"location_host": "en.wiktionary.org"},
                                   {"location_host": "en.wiktionary.org", "reachable": "no"}])
def test_malformed_redirect_result_fails_closed(entry):
    results = expected_results()
    if entry is None:
        del results["offhost_redirect"]
    else:
        results["offhost_redirect"] = entry
    assert evaluate_preflight(results).failures == (
        "offhost_redirect: missing or malformed result; the evidence is incomplete.",)


@pytest.mark.parametrize("host", [None, "en.wikipedia.org"])
def test_redirect_that_stays_on_host_is_only_a_note(host):
    results = expected_results()
    results["offhost_redirect"] = {"http_status": 200, "location_host": host}
    verdict = evaluate_preflight(results)
    assert verdict.passed
    assert "offhost_redirect not exercised: the page did not redirect to another host." in verdict.notes


def test_malformed_dns_lookup_fails_closed():
    results = expected_results()
    results["dns_lookup_unlisted"] = {"resolved": "yes"}
    assert evaluate_preflight(results).failures == (
        "dns_lookup_unlisted: missing or malformed result; the evidence is incomplete.",)


# ---------------------------------------------------------------------------
# The probe's own helper functions, run here against loopback servers only.
# Everything in PROBE before the first probe loop is definitions, so executing
# that part makes no connection.
# ---------------------------------------------------------------------------

import socket
import threading


@pytest.fixture
def probe_helpers():
    namespace = {}
    exec(PROBE.split("\nfor name, url in")[0], namespace)
    return namespace


def _serve_once(reply, kind=socket.SOCK_STREAM):
    """Start a one-shot loopback server. reply=None: accept, then close at once."""
    server = socket.socket(socket.AF_INET, kind)
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]
    if kind == socket.SOCK_STREAM:
        server.listen(1)

    def run():
        with server:
            if kind == socket.SOCK_DGRAM:
                data, address = server.recvfrom(512)
                server.sendto(data[:2] + b"\x81\x80", address)  # echo the query ID
                return
            connection, _ = server.accept()
            with connection:
                if reply is not None:
                    connection.recv(4096)
                    connection.sendall(reply)

    threading.Thread(target=run, daemon=True).start()
    return port


def _closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_tls_helper_reports_blocked_when_peer_closes_or_refuses(probe_helpers):
    tls = probe_helpers["tls_as_allowed_name"]
    assert tls("127.0.0.1", _serve_once(None))["outcome"] == "blocked"
    assert tls("127.0.0.1", _closed_port()) == {"outcome": "blocked", "error": "ECONNREFUSED"}


def test_tls_helper_reports_non_tls_answer_as_ambiguous(probe_helpers):
    # Plain text instead of TLS: neither "blocked" nor a proven identity.
    outcome = probe_helpers["tls_as_allowed_name"]("127.0.0.1", _serve_once(b"HTTP/1.1 400 Bad\r\n\r\n"))
    assert outcome["outcome"] == "tls_alert"


def test_http_helper_classifies_reply_by_location(probe_helpers, monkeypatch):
    helper = probe_helpers["http_as_allowed_name"]
    real_connect = socket.create_connection

    def aim_at(port):
        # Port 80 is fixed inside the helper; send its connection to our server instead.
        fake = type("FakeSocketModule", (), {"create_connection": staticmethod(
            lambda address, timeout: real_connect(("127.0.0.1", port), timeout))})
        monkeypatch.setitem(helper.__globals__, "socket", fake)

    aim_at(_serve_once(b"HTTP/1.1 301 Moved\r\nLocation: https://en.wikipedia.org/wiki/Boston\r\n\r\n"))
    assert helper("ignored")["outcome"] == "allowed_server"
    aim_at(_serve_once(b"HTTP/1.1 404 Not Found\r\nServer: other\r\n\r\n"))
    assert helper("ignored") == {"outcome": "other_server", "status_line": "http/1.1 404 not found"}
    aim_at(_serve_once(None))
    # Closing without reading can surface as an empty reply or a reset; both are "blocked".
    assert helper("ignored")["outcome"] == "blocked"


def test_dns_helper_needs_matching_reply_id(probe_helpers, monkeypatch):
    helper = probe_helpers["dns_udp"]
    port = _serve_once(None, kind=socket.SOCK_DGRAM)
    real_socket = socket.socket

    class ToLoopback(real_socket):
        def sendto(self, data, address):
            return super().sendto(data, ("127.0.0.1", port))

    monkeypatch.setitem(helper.__globals__, "socket", type("FakeSocketModule", (), {
        "socket": ToLoopback, "AF_INET": socket.AF_INET, "SOCK_DGRAM": socket.SOCK_DGRAM}))
    assert helper("8.8.8.8") == {"reachable": True}


def test_tls_errors_are_named_by_type_not_by_openssl_code(probe_helpers):
    # OpenSSL's SSL_ERROR_EOF is 8; as an OS errno, 8 would wrongly read ENOEXEC.
    import ssl
    assert probe_helpers["error_name"](ssl.SSLEOFError(8, "EOF occurred in violation of protocol")) == "SSLEOFError"


# ---------------------------------------------------------------------------
# Public-web mode (W1X-F02).
# ---------------------------------------------------------------------------

from crescendo_agent.e2b_preflight import (
    PUBLIC_MUST_BLOCK, PUBLIC_MUST_REACH, PUBLIC_PROBE, evaluate_public_preflight, run_public_preflight,
)


def public_results():
    """The live result of November 16, 2026 (second public run), which passed."""
    return {
        "public_example": {"reachable": True, "http_status": 200},
        "public_wikipedia": {"reachable": True, "http_status": 200},
        "public_boston_gov": {"reachable": True, "http_status": 200},
        "canary_denied": {"reachable": False, "tls": "SSLEOFError", "dns": "TimeoutError"},
        "canary_open": {"reachable": True, "tls": "verified", "dns": "answered"},
        "private_10": {"reachable": False, "error": "TimeoutError"},
        "private_172": {"reachable": False, "error": "TimeoutError"},
        "private_192": {"reachable": False, "error": "TimeoutError"},
        "cgnat_100": {"reachable": False, "error": "TimeoutError"},
        "metadata_tcp": {"reachable": True},
        "public_ipv6_tcp": {"reachable": False, "error": "ENETUNREACH"},
        "rebind_10": {"reachable": False, "error": "TimeoutError", "resolved": "10.0.0.1"},
        "rebind_192": {"reachable": False, "error": "TimeoutError", "resolved": "192.168.0.1"},
        "gateway": {"address": "169.254.0.22", "tcp_80": {"reachable": False, "error": "TimeoutError"}},
    }


def test_public_probe_compiles_and_emits_every_judged_name():
    compile(PUBLIC_PROBE, "<public probe>", "exec")
    for name in PUBLIC_MUST_REACH + PUBLIC_MUST_BLOCK:
        assert f'"{name}"' in PUBLIC_PROBE or f"'{name}'" in PUBLIC_PROBE


def test_public_live_result_passes_with_canary_and_rebinding_notes():
    verdict = evaluate_public_preflight(public_results())
    assert verdict.passed
    joined = "\n".join(verdict.notes)
    assert "the deny list is enforced" in joined
    assert "rebind_10: public DNS resolved to 10.0.0.1; connecting was blocked." in joined


@pytest.mark.parametrize("name", PUBLIC_MUST_BLOCK)
def test_public_any_denied_destination_reachable_fails(name):
    results = public_results()
    results[name] = dict(results[name], reachable=True)
    verdict = evaluate_public_preflight(results)
    assert verdict.failures == (f"{name}: a denied destination was reachable; do not enable public browsing.",)


def test_public_canary_reachable_means_deny_list_unproven():
    # The first live attempt measured TCP 443, which E2B's proxy always accepts;
    # only a real server answer counts, and a reachable canary must fail the run.
    results = public_results()
    results["canary_denied"] = {"reachable": True, "tls": "verified", "dns": "answered"}
    verdict = evaluate_public_preflight(results)
    assert not verdict.passed
    assert not any("deny list is enforced" in note for note in verdict.notes)


@pytest.mark.parametrize("name", PUBLIC_MUST_REACH)
def test_public_required_destination_unreachable_fails(name):
    results = public_results()
    results[name] = dict(results[name], reachable=False)
    assert f"{name}: unreachable; public browsing is not verified." in evaluate_public_preflight(results).failures


def test_public_missing_result_fails_closed():
    results = public_results()
    del results["rebind_10"]
    assert evaluate_public_preflight(results).failures == (
        "rebind_10: missing or malformed result; the evidence is incomplete.",)


def test_public_preflight_denies_private_ranges_plus_canary_and_cleans_up():
    from crescendo_security.policy import PRIVATE_NETWORKS
    factory = Mock()
    factory.create.return_value.commands.run.return_value.stdout = "{}"
    assert run_public_preflight(sandbox_type=factory) == {}
    network = factory.create.call_args.kwargs["network"]
    assert network == {"deny_out": [*PRIVATE_NETWORKS, "1.1.1.1/32"], "allow_public_traffic": False}
    factory.create.return_value.kill.assert_called_once_with()
