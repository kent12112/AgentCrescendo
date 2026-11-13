import json
import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

from crescendo_agent.e2b_preflight import run_preflight


def test_network_is_restricted_from_creation_and_desktop_is_destroyed():
    factory = Mock()
    sandbox = factory.create.return_value
    expected = {"allowed_wikipedia": {"reachable": True}}
    sandbox.commands.run.return_value.stdout = json.dumps(expected)

    assert run_preflight(sandbox_type=factory) == expected

    factory.create.assert_called_once_with(
        timeout=120,
        network={"deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
                 "allow_public_traffic": False},
    )
    sandbox.kill.assert_called_once_with()
    assert sandbox.commands.run.call_args.kwargs["timeout"] == 45


@pytest.mark.parametrize("external_reachable", [False, True])
def test_cli_distinguishes_local_metadata_from_external_egress(monkeypatch, external_reachable):
    monkeypatch.setenv("E2B_API_KEY", "offline-test")
    monkeypatch.setattr("crescendo_agent.e2b_preflight.run_preflight", lambda: {
        "allowed_wikipedia": {"reachable": True, "http_status": 200},
        "unlisted_example": {"reachable": external_reachable},
        "metadata_tcp": {"reachable": True},
        "private_tcp": {"reachable": False},
    })
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_preflight.py"
    if external_reachable:
        with pytest.raises(SystemExit, match="disallowed destination"):
            runpy.run_path(str(script), run_name="__main__")
    else:
        runpy.run_path(str(script), run_name="__main__")


@pytest.mark.parametrize("failure", [RuntimeError("command failed"), None])
def test_cleanup_runs_when_command_or_output_fails(failure):
    factory = Mock()
    sandbox = factory.create.return_value
    if failure is not None:
        sandbox.commands.run.side_effect = failure
    else:
        sandbox.commands.run.return_value.stdout = "not JSON"
    with pytest.raises((RuntimeError, ValueError)):
        run_preflight(sandbox_type=factory)
    sandbox.kill.assert_called_once_with()
