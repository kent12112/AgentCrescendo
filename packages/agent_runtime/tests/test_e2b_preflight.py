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
    INFORMATIONAL, MUST_BLOCK, MUST_REACH, PROBE, evaluate_preflight, run_preflight,
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
        # Set timeout to (120,).
        timeout=120,
        # Pass keyword network = a new dictionary with keys 'deny_out', 'allow_out',
        # 'allow_public_traffic'.
        network={"deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
                 # Include allow_public_traffic in this dictionary.
                 "allow_public_traffic": False},
    )
    # Call sandbox.kill.assert_called_once_with with no arguments.
    sandbox.kill.assert_called_once_with()
    # Assert that the remote command may run for 75 seconds, inside the 120-second lifetime.
    assert sandbox.commands.run.call_args.kwargs["timeout"] == 75


# Define test_probe_compiles_and_emits_every_judged_name with no parameters.
def test_probe_compiles_and_emits_every_judged_name():
    # Compile the remote source locally: a syntax error would otherwise appear only in a paid run.
    compile(PROBE, "<e2b preflight probe>", "exec")
    # Check every name the evaluator judges.
    for name in MUST_REACH + MUST_BLOCK + INFORMATIONAL:
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
