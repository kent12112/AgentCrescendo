# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import runpy: use this module through its namespace.
import runpy
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.desktop: Observation (holds current page URL, bounded text, and
# observed links).
from crescendo_agent.desktop import Observation


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("navigation_fails", [False, True])
# Define test_browser_smoke_checks_cleanup_after_success_and_failure with parameters monkeypatch,
# navigation_fails.
def test_browser_smoke_checks_cleanup_after_success_and_failure(monkeypatch, navigation_fails):
    # Set factory to Mock().
    factory = Mock()
    # Set factory.create.return_value.is_running.return_value to False.
    factory.create.return_value.is_running.return_value = False
    # Set desktop to Mock().
    desktop = Mock()
    # Set url to 'https://en.wikipedia.org/wiki/Boston'.
    url = "https://en.wikipedia.org/wiki/Boston"
    # Set desktop.observe.return_value to Observation(url, 'Boston is a city.').
    desktop.observe.return_value = Observation(url, "Boston is a city.")
    # Set desktop.visited to [url].
    desktop.visited = [url]
    # Set desktop.navigate.side_effect to RuntimeError('Browser startup failed') if
    # navigation_fails, otherwise [None, ValueError('denied'), ValueError('denied')].
    desktop.navigate.side_effect = (
        # Call RuntimeError with the arguments shown.
        RuntimeError("Browser startup failed") if navigation_fails
        # Call ValueError with the arguments shown.
        else [None, ValueError("denied"), ValueError("denied")]
    )

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define fake_open with parameters grant, sandbox_type.
    def fake_open(grant, *, sandbox_type):
        # Set sandbox to sandbox_type.create().
        sandbox = sandbox_type.create()
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give desktop to the caller and pause here until execution resumes.
            yield desktop
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Ask the provider to terminate sandbox.
            sandbox.kill()

    # Call monkeypatch.setattr with 'crescendo_agent.e2b_desktop.open_e2b_desktop', fake_open.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_browser_smoke.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_browser_smoke.py"
    # Set run_smoke to runpy.run_path(str(script))['run_smoke'].
    run_smoke = runpy.run_path(str(script))["run_smoke"]
    # Check whether navigation_fails.
    if navigation_fails:
        # Use pytest.raises(RuntimeError, match='Browser startup failed'); leave the context and run
        # its cleanup when this block ends.
        with pytest.raises(RuntimeError, match="Browser startup failed"):
            # Call run_smoke with factory.
            run_smoke(factory)
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Call run_smoke with factory.
        run_smoke(factory)
    # Call factory.create.return_value.kill.assert_called_once_with with no arguments.
    factory.create.return_value.kill.assert_called_once_with()
    # Call factory.create.return_value.is_running.assert_called_once_with with no arguments.
    factory.create.return_value.is_running.assert_called_once_with(request_timeout=10)


# Define test_browser_smoke_rejects_missing_key with parameters monkeypatch.
def test_browser_smoke_rejects_missing_key(monkeypatch):
    # Call monkeypatch.delenv with 'E2B_API_KEY'.
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_browser_smoke.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_browser_smoke.py"
    # Use pytest.raises(SystemExit, match='Set E2B_API_KEY'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(SystemExit, match="Set E2B_API_KEY"):
        # Call runpy.run_path with script converted to a string.
        runpy.run_path(str(script), run_name="__main__")
