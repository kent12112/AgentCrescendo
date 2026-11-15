# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: Import runpy: use this module through its namespace.
import runpy
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.e2b_preflight, import run_preflight (a dependency used below).
from crescendo_agent.e2b_preflight import run_preflight


# Learn: Test network is restricted from creation and desktop is destroyed. pytest supplies named fixtures
# and checks assertions below.
def test_network_is_restricted_from_creation_and_desktop_is_destroyed():
    # Learn: Set factory to Mock().
    factory = Mock()
    # Learn: Set sandbox to factory.create.return_value; the E2B desktop instance; its owner must attempt
    # cleanup.
    sandbox = factory.create.return_value
    # Learn: Set expected to a new dictionary with keys 'allowed_wikipedia'; the expected credential or
    # fixture result used in this comparison.
    expected = {"allowed_wikipedia": {"reachable": True}}
    # Learn: Set sandbox.commands.run.return_value.stdout to json.dumps(expected). Serialize structured data
    # to JSON text.
    sandbox.commands.run.return_value.stdout = json.dumps(expected)

    # Learn: Assert that run_preflight(sandbox_type=factory) equals expected. If false, this check fails
    # with AssertionError.
    assert run_preflight(sandbox_type=factory) == expected

    # Learn: Verify the fake dependency ran exactly once with these arguments on factory.create.
    factory.create.assert_called_once_with(
        # Learn: Pass keyword timeout = 120.
        timeout=120,
        # Learn: Pass keyword network = a new dictionary with keys 'deny_out', 'allow_out',
        # 'allow_public_traffic'.
        network={"deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
                 # Learn: Define this named mapping field: "allow_public_traffic": False},. The key selects
                 # the schema/configuration value.
                 "allow_public_traffic": False},
    # Learn: Close the argument list for factory.create.assert_called_once_with; the grouped expression
    # remains one call.
    )
    # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.kill.
    sandbox.kill.assert_called_once_with()
    # Learn: Assert that sandbox.commands.run.call_args.kwargs['timeout'] equals 45. If false, this check
    # fails with AssertionError.
    assert sandbox.commands.run.call_args.kwargs["timeout"] == 45


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("external_reachable", [False, True])
# Learn: Test cli distinguishes local metadata from external egress. pytest supplies named fixtures and
# checks assertions below.
def test_cli_distinguishes_local_metadata_from_external_egress(monkeypatch, external_reachable):
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'E2B_API_KEY',
    # 'offline-test'.
    monkeypatch.setenv("E2B_API_KEY", "offline-test")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.e2b_preflight.run_preflight", lambda: {
        # Learn: Define this named mapping field: "allowed_wikipedia": {"reachable": True, "http_status":
        # 200},. The key selects the schema/configuration value.
        "allowed_wikipedia": {"reachable": True, "http_status": 200},
        # Learn: Define this named mapping field: "unlisted_example": {"reachable": external_reachable},.
        # The key selects the schema/configuration value.
        "unlisted_example": {"reachable": external_reachable},
        # Learn: Define this named mapping field: "metadata_tcp": {"reachable": True},. The key selects the
        # schema/configuration value.
        "metadata_tcp": {"reachable": True},
        # Learn: Define this named mapping field: "private_tcp": {"reachable": False},. The key selects the
        # schema/configuration value.
        "private_tcp": {"reachable": False},
    # Learn: Close this dict literal; delimiters group the values into one object.
    })
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_preflight.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_preflight.py"
    # Learn: Take this branch only if external_reachable.
    if external_reachable:
        # Learn: Enter pytest.raises(SystemExit, match='disallowed destination'). The context manager
        # controls setup/exit; inspect it for the actual cleanup behavior.
        with pytest.raises(SystemExit, match="disallowed destination"):
            # Learn: Call runpy.run_path with the arguments shown.
            runpy.run_path(str(script), run_name="__main__")
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(script), run_name="__main__")


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("failure", [RuntimeError("command failed"), None])
# Learn: Test cleanup runs when command or output fails. pytest supplies named fixtures and checks
# assertions below.
def test_cleanup_runs_when_command_or_output_fails(failure):
    # Learn: Set factory to Mock().
    factory = Mock()
    # Learn: Set sandbox to factory.create.return_value; the E2B desktop instance; its owner must attempt
    # cleanup.
    sandbox = factory.create.return_value
    # Learn: Take this branch only if failure is not None (no value).
    if failure is not None:
        # Learn: Set sandbox.commands.run.side_effect to failure.
        sandbox.commands.run.side_effect = failure
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Set sandbox.commands.run.return_value.stdout to 'not JSON'.
        sandbox.commands.run.return_value.stdout = "not JSON"
    # Learn: Enter pytest.raises((RuntimeError, ValueError)). The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with pytest.raises((RuntimeError, ValueError)):
        # Learn: Call run_preflight with the arguments shown.
        run_preflight(sandbox_type=factory)
    # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.kill.
    sandbox.kill.assert_called_once_with()
