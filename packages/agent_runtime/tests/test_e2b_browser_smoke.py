from contextlib import contextmanager
from pathlib import Path
import runpy
from unittest.mock import Mock

import pytest

from crescendo_agent.desktop import Observation


@pytest.mark.parametrize("navigation_fails", [False, True])
def test_browser_smoke_checks_cleanup_after_success_and_failure(monkeypatch, navigation_fails):
    factory = Mock()
    factory.create.return_value.is_running.return_value = False
    desktop = Mock()
    url = "https://en.wikipedia.org/wiki/Boston"
    desktop.observe.return_value = Observation(url, "Boston is a city.")
    desktop.visited = [url]
    desktop.navigate.side_effect = (
        RuntimeError("Browser startup failed") if navigation_fails
        else [None, ValueError("denied"), ValueError("denied")]
    )

    @contextmanager
    def fake_open(grant, *, sandbox_type):
        sandbox = sandbox_type.create()
        try:
            yield desktop
        finally:
            sandbox.kill()

    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_browser_smoke.py"
    run_smoke = runpy.run_path(str(script))["run_smoke"]
    if navigation_fails:
        with pytest.raises(RuntimeError, match="Browser startup failed"):
            run_smoke(factory)
    else:
        run_smoke(factory)
    factory.create.return_value.kill.assert_called_once_with()
    factory.create.return_value.is_running.assert_called_once_with(request_timeout=10)


def test_browser_smoke_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_browser_smoke.py"
    with pytest.raises(SystemExit, match="Set E2B_API_KEY"):
        runpy.run_path(str(script), run_name="__main__")
