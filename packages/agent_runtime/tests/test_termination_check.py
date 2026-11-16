"""Offline tests for scripts/e2b_termination_check.py. A fake provider replaces E2B."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from e2b import SandboxNotFoundException

from crescendo_agent.desktop import Observation

SCRIPT = Path(__file__).parents[3] / "scripts" / "e2b_termination_check.py"


def load_script():
    """Load the script as a module so tests can replace its globals."""
    spec = importlib.util.spec_from_file_location("e2b_termination_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProvider:
    """Plays E2B's control plane: tracks which sandbox IDs exist and in what state."""

    def __init__(self, gone_after_lookups=0):
        self.states = {}
        self.killed = []
        # How many lookups return "running" before the sandbox disappears.
        self.gone_after_lookups = gone_after_lookups
        self.lookups = 0

    def create(self, **kwargs):
        sandbox_id = f"sbx-{len(self.states) + 1}"
        self.states[sandbox_id] = "running"
        return NS(sandbox_id=sandbox_id, create_kwargs=kwargs)

    def get_info(self, sandbox_id):
        self.lookups += 1
        state = self.states.get(sandbox_id)
        if state == "killed" and self.lookups > self.gone_after_lookups:
            state = None
        if state is None:
            raise SandboxNotFoundException(f"Sandbox {sandbox_id} not found")
        end_at = datetime.now(timezone.utc) + timedelta(seconds=1)
        return NS(state=NS(value="running" if state == "killed" else state),
                  started_at=end_at - timedelta(seconds=60), end_at=end_at,
                  lifecycle={"on_timeout": "kill", "auto_resume": False})

    def kill(self, sandbox_id):
        self.killed.append(sandbox_id)
        self.states[sandbox_id] = "killed"
        return True


def fake_open_factory():
    """Mimics open_e2b_desktop: create, yield a desktop, kill in finally."""
    desktop = NS(navigate=lambda url: None,
                 observe=lambda: Observation("https://en.wikipedia.org/wiki/Boston", "Boston"))

    @contextmanager
    def fake_open(grant, *, sandbox_type, lifetime_seconds=180):
        sandbox = sandbox_type.create(timeout=lifetime_seconds)
        try:
            yield desktop
        finally:
            sandbox_type_api.kill(sandbox.sandbox_id)

    sandbox_type_api = None

    def bind(api):
        nonlocal sandbox_type_api
        sandbox_type_api = api
        return fake_open
    return bind


NO_WAIT = {"poll_seconds": 0, "sleep": lambda seconds: None}


@pytest.mark.parametrize("scenario", ["normal", "failure"])
def test_cleanup_scenarios_confirm_through_provider(monkeypatch, scenario):
    check = load_script()
    provider = FakeProvider(gone_after_lookups=2)
    monkeypatch.setattr(check, "open_e2b_desktop", fake_open_factory()(provider))
    check.SCENARIOS[scenario](provider, **NO_WAIT)
    assert provider.killed == ["sbx-1"]


def test_failure_scenario_rejects_unrelated_errors(monkeypatch):
    check = load_script()
    provider = FakeProvider()
    monkeypatch.setattr(check, "open_e2b_desktop", fake_open_factory()(provider))
    monkeypatch.setattr(check, "load_page", lambda desktop: (_ for _ in ()).throw(OSError("net")))
    # A real setup error must surface, not be mistaken for the deliberate failure.
    with pytest.raises(OSError, match="net"):
        check.run_failure(provider, **NO_WAIT)


def test_sandbox_that_never_disappears_is_killed_and_fails():
    check = load_script()
    provider = FakeProvider()
    sandbox = provider.create()
    ticks = iter(range(0, 1000, 10))
    with pytest.raises(RuntimeError, match="still 'running'.*kill retried"):
        check.confirm_gone(provider, sandbox.sandbox_id, "normal", 30,
                           clock=lambda: next(ticks), **NO_WAIT)
    assert provider.killed == [sandbox.sandbox_id]


def test_paused_sandbox_counts_as_not_destroyed():
    check = load_script()
    provider = FakeProvider()
    sandbox = provider.create()
    provider.states[sandbox.sandbox_id] = "paused"
    assert check.wait_until_gone(provider, sandbox.sandbox_id, 30, **NO_WAIT) is None


def child_result(provider, *, returncode=0, ready=True):
    sandbox = provider.create()
    stdout = f"SANDBOX_ID={sandbox.sandbox_id}\n" + ("CHILD_READY\n" if ready else "")
    return NS(returncode=returncode, stdout=stdout, stderr="")


def test_abandon_waits_for_provider_timer_without_killing():
    check = load_script()
    provider = FakeProvider()
    result = child_result(provider)

    # The "timer" fires on the third lookup: the provider removes the sandbox itself.
    def lookup(sandbox_id, original=provider.get_info):
        if provider.lookups >= 3:
            provider.states[sandbox_id] = None
        return original(sandbox_id)
    provider.get_info = lookup

    check.run_abandon(provider, run_child=lambda: result, **NO_WAIT)
    # Passing must come from the provider's timer, never from our own kill().
    assert provider.killed == []


def test_abandon_rejects_child_that_failed_before_abandoning():
    check = load_script()
    provider = FakeProvider()
    result = child_result(provider, returncode=1, ready=False)
    with pytest.raises(RuntimeError, match="failed before abandoning"):
        check.run_abandon(provider, run_child=lambda: result, **NO_WAIT)
    assert provider.killed == ["sbx-1"]


def test_abandon_rejects_child_without_sandbox_id():
    check = load_script()
    with pytest.raises(RuntimeError, match="no sandbox ID"):
        check.run_abandon(FakeProvider(), run_child=lambda: NS(returncode=1, stdout="", stderr=""))


def test_debug_mode_is_refused(monkeypatch):
    check = load_script()
    monkeypatch.setattr(check, "load_local_env", lambda: None)
    monkeypatch.setenv("E2B_API_KEY", "test-key")
    monkeypatch.setenv("E2B_DEBUG", "true")
    with pytest.raises(SystemExit, match="E2B_DEBUG"):
        check.main([])
