"""Source startup failures must remain separate from model/click failures."""
from contextlib import contextmanager
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeout
import pytest

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_agent.vision import Screenshot
from crescendo_security.policy import TaskGrant


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "e2b_click_demo.py"
load_source = runpy.run_path(str(SCRIPT))["load_source"]
URL = "https://en.wikipedia.org/wiki/Boston"
GOOD = {"status": 200, "article": True, "title": "Boston - Wikipedia"}
ERROR = {"status": 503, "article": False, "title": "Wikimedia Error"}
PNG = Screenshot(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
    "0000000b4944415478da63fcff1f0003030200efa3875b0000000049454e44ae426082"))


def source_desktop(outcomes):
    desktop = Mock()
    outcomes = iter(outcomes)

    def navigate(url):
        assert url == URL
        outcome = next(outcomes)
        desktop.last_navigation_status = outcome.get("status")
        desktop.last_navigation_retry_after = outcome.get("retry_after")
        desktop.page.title.return_value = outcome.get("title", "Error")
        desktop.page.locator.return_value.count.return_value = int(outcome.get("article", False))
        if "error" in outcome:
            raise outcome["error"]

    desktop.navigate.side_effect = navigate
    desktop.capture_screen.return_value = PNG
    return desktop


def test_successful_article_is_used_without_an_extra_navigation():
    desktop = source_desktop([GOOD])
    attempts = load_source(desktop)
    assert attempts[-1]["ready"] is True
    desktop.navigate.assert_called_once_with(URL)
    desktop.page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("failure, milliseconds", [
    (ERROR, 5000),
    ({**ERROR, "status": 429, "retry_after": "12"}, 12000),
    ({"error": PlaywrightTimeout("private request details")}, 5000),
])
def test_transient_failure_retries_same_url_once_and_then_accepts_article(failure, milliseconds):
    desktop = source_desktop([failure, GOOD])
    records = []
    attempts = load_source(desktop, on_attempt=records.append)
    assert len(attempts) == 2 and attempts[-1]["ready"]
    assert records == attempts and not attempts[0]["ready"]
    desktop.page.wait_for_timeout.assert_called_once_with(milliseconds)
    assert [call.args for call in desktop.navigate.call_args_list] == [(URL,), (URL,)]
    assert "private request details" not in json.dumps(attempts)


@pytest.mark.parametrize("failure", [
    {**ERROR, "status": 403},
    {**ERROR, "status": 404, "article": True},
    {**ERROR, "status": 200},
    {**GOOD, "status": None},
    {"error": PlaywrightError("certificate failure")},
    {**ERROR, "retry_after": "60"},
    {**ERROR, "retry_after": "NaN"},
    {**ERROR, "retry_after": "-1"},
    {**ERROR, "retry_after": "not a numeric delay"},
])
def test_refusals_unknown_failures_and_unacceptable_waits_are_not_retried(failure):
    desktop = source_desktop([failure, GOOD])
    attempts = load_source(desktop)
    assert not attempts[-1]["ready"] and len(attempts) == 1
    desktop.navigate.assert_called_once_with(URL)
    desktop.page.wait_for_timeout.assert_not_called()


def test_second_source_failure_exhausts_retry_budget():
    desktop = source_desktop([ERROR, ERROR, GOOD])
    attempts = load_source(desktop)
    assert len(attempts) == 2 and not attempts[-1]["ready"]
    assert desktop.navigate.call_count == 2
    desktop.page.wait_for_timeout.assert_called_once_with(5000)


def test_navigation_metadata_is_reset_after_a_later_navigation_timeout():
    page, session = Mock(), Mock()
    grant = TaskGrant("source", frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))
    desktop = E2BDesktop(page, session, grant)
    page.goto.return_value = NS(status=503, headers={"retry-after": "12", "private-header": "secret"})
    desktop.navigate(URL)
    assert desktop.last_navigation_status == 503 and desktop.last_navigation_retry_after == "12"
    page.goto.side_effect = PlaywrightTimeout("slow network")
    with pytest.raises(PlaywrightTimeout):
        desktop.navigate(URL)
    assert desktop.last_navigation_status is None and desktop.last_navigation_retry_after is None


@pytest.mark.parametrize("status, expected_attempts", [(403, 1), (503, 2)])
@pytest.mark.parametrize("click_mode", ["links", "coordinates"])
def test_cli_saves_startup_evidence_without_calling_model(tmp_path, monkeypatch, capsys,
                                                       status, expected_attempts, click_mode):
    main = runpy.run_path(str(SCRIPT))["main"]
    desktop = source_desktop([{**ERROR, "status": status}] * expected_attempts)
    model, cleanup = Mock(), []
    model.model = "test-model"

    @contextmanager
    def open_desktop(grant, **kwargs):
        assert ("read_visible_links" in grant.allowed_tools) is (click_mode == "links")
        try:
            yield desktop
        finally:
            cleanup.append("closed")

    monkeypatch.setitem(main.__globals__, "load_local_env", lambda: None)
    monkeypatch.setitem(main.__globals__, "open_e2b_desktop", open_desktop)
    monkeypatch.setitem(main.__globals__, "GroqVision", lambda *args, **kwargs: model)
    monkeypatch.setenv("E2B_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--save-screenshots", "--click-mode", click_mode])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="SOURCE UNAVAILABLE.*No model calls"):
        main()
    assert cleanup == ["closed"]
    model.decide.assert_not_called()
    desktop.click.assert_not_called()
    result_file, = tmp_path.glob(".demo-artifacts/click-*/result.json")
    result = json.loads(result_file.read_text())
    assert result["status"] == "source_unavailable" and result["model_calls"] == 0
    assert len(result["source_attempts"]) == expected_attempts
    assert result_file.with_name("source-attempts.json").exists()
    assert len(list(result_file.parent.glob("source-*.png"))) == expected_attempts
    assert f"HTTP {status}" in capsys.readouterr().out
