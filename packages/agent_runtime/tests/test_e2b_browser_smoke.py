# Learn: From contextlib, import contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: Import runpy: use this module through its namespace.
import runpy
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.desktop, import Observation (holds current page URL, bounded text, and
# observed links).
from crescendo_agent.desktop import Observation


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("navigation_fails", [False, True])
# Learn: Test browser smoke checks cleanup after success and failure. pytest supplies named fixtures and
# checks assertions below.
def test_browser_smoke_checks_cleanup_after_success_and_failure(monkeypatch, navigation_fails):
    # Learn: Set factory to Mock().
    factory = Mock()
    # Learn: Set factory.create.return_value.is_running.return_value to False.
    factory.create.return_value.is_running.return_value = False
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set url to 'https://en.wikipedia.org/wiki/Boston'; the destination or current page address.
    url = "https://en.wikipedia.org/wiki/Boston"
    # Learn: Set desktop.observe.return_value to Observation(url, 'Boston is a city.').
    desktop.observe.return_value = Observation(url, "Boston is a city.")
    # Learn: Set desktop.visited to a new list containing url; the successful navigation destinations
    # observed by the adapter.
    desktop.visited = [url]
    # Learn: Set desktop.navigate.side_effect to RuntimeError('Browser startup failed') when
    # navigation_fails, otherwise a new list containing None (no value), ValueError('denied'),
    # ValueError('denied').
    desktop.navigate.side_effect = (
        # Learn: Call RuntimeError with the arguments shown.
        RuntimeError("Browser startup failed") if navigation_fails
        # Learn: Call ValueError with the arguments shown.
        else [None, ValueError("denied"), ValueError("denied")]
    # Learn: Close the multi-line expression; indentation inside brackets is for readability, not a new
    # block.
    )

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Learn: Define fake_open(grant, sandbox_type). The body runs when called, not when defined.
    def fake_open(grant, *, sandbox_type):
        # Learn: Set sandbox to sandbox_type.create(); the E2B desktop instance; its owner must attempt
        # cleanup. Create the requested SDK resource or provider response.
        sandbox = sandbox_type.create()
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Yield desktop to the with-block/request; resume here for cleanup afterward.
            yield desktop
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Ask E2B to terminate the sandbox; successful return alone is not independent
            # termination evidence on sandbox.
            sandbox.kill()

    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_browser_smoke.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_browser_smoke.py"
    # Learn: Set run_smoke to runpy.run_path(str(script))['run_smoke'].
    run_smoke = runpy.run_path(str(script))["run_smoke"]
    # Learn: Take this branch only if navigation_fails.
    if navigation_fails:
        # Learn: Enter pytest.raises(RuntimeError, match='Browser startup failed'). The context manager
        # controls setup/exit; inspect it for the actual cleanup behavior.
        with pytest.raises(RuntimeError, match="Browser startup failed"):
            # Learn: Call run_smoke with the arguments shown.
            run_smoke(factory)
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Call run_smoke with the arguments shown.
        run_smoke(factory)
    # Learn: Verify the fake dependency ran exactly once with these arguments on
    # factory.create.return_value.kill.
    factory.create.return_value.kill.assert_called_once_with()
    # Learn: Verify the fake dependency ran exactly once with these arguments on
    # factory.create.return_value.is_running.
    factory.create.return_value.is_running.assert_called_once_with(request_timeout=10)


# Learn: Test browser smoke rejects missing key. pytest supplies named fixtures and checks assertions below.
def test_browser_smoke_rejects_missing_key(monkeypatch):
    # Learn: Call monkeypatch.delenv with the arguments shown.
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_browser_smoke.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_browser_smoke.py"
    # Learn: Enter pytest.raises(SystemExit, match='Set E2B_API_KEY'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(SystemExit, match="Set E2B_API_KEY"):
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(script), run_name="__main__")
