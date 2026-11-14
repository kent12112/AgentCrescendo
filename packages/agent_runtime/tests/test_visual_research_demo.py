from contextlib import contextmanager
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from crescendo_agent.model import Entry

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "e2b_visual_research_demo.py"
DEMO = runpy.run_path(str(SCRIPT))


@pytest.mark.parametrize("answer,page_text,visible,passed,reason", [
    ("617565", "GNIS feature ID 617565", True, True, "PASS"),
    ("617565", "GNIS feature ID 999999", True, False, "FIXTURE CHANGED"),
    ("617566", "GNIS feature ID 617565", True, False, "does not contain"),
    (None, "GNIS feature ID 617565", True, False, "does not contain"),
    # Correct value but not on screen at finish: could be memorized or guessed, not seen.
    ("617565", "GNIS feature ID 617565", False, False, "not on screen"),
])
def test_grade_requires_correct_supported_and_visible(answer, page_text, visible, passed, reason):
    ok, message = DEMO["grade"](answer, "617565", page_text, visible)
    assert ok is passed
    assert reason in message


def test_short_answer_validator():
    assert DEMO["validate_short_answer"]("617565") is None
    assert "200 characters" in DEMO["validate_short_answer"]("x" * 201)


def test_model_tools_lists_only_proposed_actions():
    transcript = [Entry("goal", "g"), Entry("observation", "o"),
                  Entry("action", '{"tool": "scroll", "args": {}}'), Entry("denied", "no"),
                  Entry("action", '{"tool": "finish", "args": {}}')]
    assert DEMO["model_tools"](transcript) == ["scroll", "finish"]


def test_decision_lines_show_reason_or_placeholder():
    transcript = [Entry("action", '{"tool": "scroll", "args": {"direction": "down", "amount": 5}, '
                                  '"reason": "Infobox continues below"}'),
                  Entry("action", '{"tool": "finish", "args": {"answer": "617565"}}')]
    assert DEMO["decision_lines"](transcript) == [
        "  1. scroll(direction='down', amount=5) — reason: 'Infobox continues below'",
        "  2. finish(answer='617565') — reason: '(none given)'",
    ]


def run_demo(monkeypatch, *, answer="617565", final_url=None, failure=False, article_count=1):
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    monkeypatch.setattr(sys, "argv", ["e2b_visual_research_demo.py"])
    events = []
    desktop = Mock()
    desktop.page.url = final_url or DEMO["SOURCE_URL"]
    desktop.page.evaluate.return_value = True
    desktop.page.locator.return_value.inner_text.return_value = "GNIS feature ID 617565"
    desktop.page.locator.return_value.count.return_value = article_count
    desktop.page.title.return_value = "Wikimedia Error"
    desktop.blocked_requests = []
    desktop.navigate.side_effect = lambda url: events.append(("navigate", url))

    @contextmanager
    def open_desktop(grant, *, lifetime_seconds):
        assert lifetime_seconds == 300
        events.append(("open", grant))
        try:
            yield desktop
        finally:
            events.append(("closed",))

    def run(goal, grant, desk, model, **kwargs):
        events.append(("run", goal, kwargs["max_steps"]))
        if failure:
            raise RuntimeError("Vision failed")
        return NS(status="finished", answer=answer, denied=[],
                  transcript=[Entry("action", '{"tool": "scroll", "args": {}}'),
                              Entry("action", '{"tool": "finish", "args": {}}')])

    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: NS(model=name))
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    return events


def test_demo_navigates_first_hides_expected_value_and_cleans_up(monkeypatch, capsys):
    events = run_demo(monkeypatch)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    out = capsys.readouterr().out
    grant = events[0][1]
    assert grant.allowed_hosts == frozenset({"en.wikipedia.org"})
    assert "click" not in grant.allowed_tools
    assert events[1] == ("navigate", DEMO["SOURCE_URL"])
    _, goal, max_steps = events[2]
    assert "617565" not in goal and max_steps == 8
    assert events[-1] == ("closed",)
    assert "PASS" in out and "Cited answer: 617565 [https://en.wikipedia.org/wiki/Boston]" in out


def test_demo_wrong_answer_fails_after_cleanup(monkeypatch):
    events = run_demo(monkeypatch, answer="123456")
    with pytest.raises(SystemExit, match="does not contain"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert events[-1] == ("closed",)


def test_demo_rejects_finishing_on_unexpected_host(monkeypatch):
    run_demo(monkeypatch, final_url="https://evil.com/")
    with pytest.raises(SystemExit, match="unexpected page"):
        runpy.run_path(str(SCRIPT), run_name="__main__")


def test_demo_stops_before_model_calls_when_source_page_is_an_error(monkeypatch):
    events = run_demo(monkeypatch, article_count=0)
    with pytest.raises(SystemExit, match="SOURCE UNAVAILABLE.*Wikimedia Error.*No model calls"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert not any(event[0] == "run" for event in events)
    assert events[-1] == ("closed",)


def test_demo_agent_failure_still_cleans_up(monkeypatch):
    events = run_demo(monkeypatch, failure=True)
    with pytest.raises(RuntimeError, match="Vision failed"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert events[-1] == ("closed",)
