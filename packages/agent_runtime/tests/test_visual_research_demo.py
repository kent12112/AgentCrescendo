# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import runpy: use this module through its namespace.
import runpy
# Import sys: provides process details and standard input/output streams.
import sys
# Import from types: SimpleNamespace as NS (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace as NS
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.model: Entry (represents one typed transcript item sent to the model).
from crescendo_agent.model import Entry

# Set SCRIPT to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
# 'e2b_visual_research_demo.py'.
SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "e2b_visual_research_demo.py"
# Set DEMO to runpy.run_path(str(SCRIPT)).
DEMO = runpy.run_path(str(SCRIPT))


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("answer,page_text,visible,passed,reason", [
    # Add this item to the surrounding list: ("617565", "GNIS feature ID 617565", True, True,
    # "PASS"),.
    ("617565", "GNIS feature ID 617565", True, True, "PASS"),
    # Add this item to the surrounding list: ("617565", "GNIS feature ID 999999", True, False,
    # "FIXTURE CHANGED"),.
    ("617565", "GNIS feature ID 999999", True, False, "FIXTURE CHANGED"),
    # Add this item to the surrounding list: ("617566", "GNIS feature ID 617565", True, False, "does
    # not contain"),.
    ("617566", "GNIS feature ID 617565", True, False, "does not contain"),
    # Add this item to the surrounding list: (None, "GNIS feature ID 617565", True, False, "does not
    # contain"),.
    (None, "GNIS feature ID 617565", True, False, "does not contain"),
    # Correct value but not on screen at finish: could be memorized or guessed, not seen.
    # Add this item to the surrounding list: ("617565", "GNIS feature ID 617565", False, False, "not
    # on screen"),.
    ("617565", "GNIS feature ID 617565", False, False, "not on screen"),
])
# Define test_grade_requires_correct_supported_and_visible with parameters answer, page_text,
# visible, passed, reason.
def test_grade_requires_correct_supported_and_visible(answer, page_text, visible, passed, reason):
    # Set (ok, message) to DEMO['grade'](answer, '617565', page_text, visible).
    ok, message = DEMO["grade"](answer, "617565", page_text, visible)
    # Assert that ok is passed. If false, this check fails with AssertionError.
    assert ok is passed
    # Assert that reason is in message. If false, this check fails with AssertionError.
    assert reason in message


# Define test_short_answer_validator with no parameters.
def test_short_answer_validator():
    # Assert that DEMO['validate_short_answer']('617565') is None (no value). If false, this check
    # fails with AssertionError.
    assert DEMO["validate_short_answer"]("617565") is None
    # Assert that '200 characters' is in DEMO['validate_short_answer']('x' * 201). If false, this
    # check fails with AssertionError.
    assert "200 characters" in DEMO["validate_short_answer"]("x" * 201)


# Define test_model_tools_lists_only_proposed_actions with no parameters.
def test_model_tools_lists_only_proposed_actions():
    # Build transcript from the entries below.
    transcript = [Entry("goal", "g"), Entry("observation", "o"),
                  # Call Entry with the arguments shown.
                  Entry("action", '{"tool": "scroll", "args": {}}'), Entry("denied", "no"),
                  # Call Entry with the arguments shown.
                  Entry("action", '{"tool": "finish", "args": {}}')]
    # Assert that DEMO['model_tools'](transcript) equals a new list containing 'scroll', 'finish'.
    # If false, this check fails with AssertionError.
    assert DEMO["model_tools"](transcript) == ["scroll", "finish"]


# Define test_decision_lines_show_reason_or_placeholder with no parameters.
def test_decision_lines_show_reason_or_placeholder():
    # Build transcript from the entries below.
    transcript = [Entry("action", '{"tool": "scroll", "args": {"direction": "down", "amount": 5}, '
                                  '"reason": "Infobox continues below"}'),
                  # Call Entry with the arguments shown.
                  Entry("action", '{"tool": "finish", "args": {"answer": "617565"}}')]
    # Assert that DEMO['decision_lines'](transcript) equals a new list containing " 1.
    # scroll(direction='down', amount=5) — reason: 'Infobox continues below'", " 2.
    # finish(answer='617565') — reason: '(none given)'". If false, this check fails with
    # AssertionError.
    assert DEMO["decision_lines"](transcript) == [
        "  1. scroll(direction='down', amount=5) — reason: 'Infobox continues below'",
        "  2. finish(answer='617565') — reason: '(none given)'",
    ]


# Define run_demo with parameters monkeypatch, answer, final_url, failure, article_count.
def run_demo(monkeypatch, *, answer="617565", final_url=None, failure=False, article_count=1):
    # Call monkeypatch.setenv with 'E2B_API_KEY', 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Call monkeypatch.setenv with 'GROQ_API_KEY', 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Call monkeypatch.setattr with sys, 'argv', ['e2b_visual_research_demo.py'].
    monkeypatch.setattr(sys, "argv", ["e2b_visual_research_demo.py"])
    # Set events to an empty list.
    events = []
    # Set desktop to Mock().
    desktop = Mock()
    # Set desktop.page.url to final_url or DEMO['SOURCE_URL'].
    desktop.page.url = final_url or DEMO["SOURCE_URL"]
    # Set desktop.page.evaluate.return_value to True.
    desktop.page.evaluate.return_value = True
    # Set desktop.page.locator.return_value.inner_text.return_value to 'GNIS feature ID 617565'.
    desktop.page.locator.return_value.inner_text.return_value = "GNIS feature ID 617565"
    # Set desktop.page.locator.return_value.count.return_value to article_count.
    desktop.page.locator.return_value.count.return_value = article_count
    # Set desktop.page.title.return_value to 'Wikimedia Error'.
    desktop.page.title.return_value = "Wikimedia Error"
    # Set desktop.blocked_requests to an empty list.
    desktop.blocked_requests = []
    # Set desktop.navigate.side_effect to a function that returns events.append(('navigate', url))
    # when called.
    desktop.navigate.side_effect = lambda url: events.append(("navigate", url))

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define open_desktop with parameters grant, lifetime_seconds.
    def open_desktop(grant, *, lifetime_seconds):
        # Assert that lifetime_seconds equals 300. If false, this check fails with AssertionError.
        assert lifetime_seconds == 300
        # Append ('open', grant) to events.
        events.append(("open", grant))
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give desktop to the caller and pause here until execution resumes.
            yield desktop
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Append ('closed',) to events.
            events.append(("closed",))

    # Define run with parameters goal, grant, desk, model.
    def run(goal, grant, desk, model, **kwargs):
        # Append ('run', goal, kwargs['max_steps']) to events.
        events.append(("run", goal, kwargs["max_steps"]))
        # Check whether failure.
        if failure:
            # Raise RuntimeError('Vision failed') to stop the normal path.
            raise RuntimeError("Vision failed")
        return NS(status="finished", answer=answer, denied=[],
                  # Pass keyword transcript = a new list containing Entry('action', '{"tool":
                  # "scroll", "args": {}}'), Entry('action', '{"tool": "finish", "args": {}}').
                  transcript=[Entry("action", '{"tool": "scroll", "args": {}}'),
                              # Call Entry with the arguments shown.
                              Entry("action", '{"tool": "finish", "args": {}}')])

    # Call monkeypatch.setattr with 'crescendo_agent.e2b_desktop.open_e2b_desktop', open_desktop.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    # Call monkeypatch.setattr with 'crescendo_agent.vision.GroqVision', a function that returns
    # NS(model=name) when called.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: NS(model=name))
    # Call monkeypatch.setattr with 'crescendo_agent.vision_loop.run_vision_agent', run.
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    # Return events.
    return events


# Define test_demo_navigates_first_hides_expected_value_and_cleans_up with parameters monkeypatch,
# capsys.
def test_demo_navigates_first_hides_expected_value_and_cleans_up(monkeypatch, capsys):
    # Set events to run_demo(monkeypatch).
    events = run_demo(monkeypatch)
    # Call runpy.run_path with SCRIPT converted to a string.
    runpy.run_path(str(SCRIPT), run_name="__main__")
    # Set out to capsys.readouterr().out.
    out = capsys.readouterr().out
    # Set grant to events[0][1].
    grant = events[0][1]
    # Assert that grant.allowed_hosts equals frozenset({'en.wikipedia.org'}). If false, this check
    # fails with AssertionError.
    assert grant.allowed_hosts == frozenset({"en.wikipedia.org"})
    # Assert that 'click' is not in grant.allowed_tools. If false, this check fails with
    # AssertionError.
    assert "click" not in grant.allowed_tools
    # Assert that events[1] equals the tuple ('navigate', DEMO['SOURCE_URL']) (positional values).
    # If false, this check fails with AssertionError.
    assert events[1] == ("navigate", DEMO["SOURCE_URL"])
    # Set (_, goal, max_steps) to events[2].
    _, goal, max_steps = events[2]
    # Assert that '617565' is not in goal AND max_steps equals 8. If false, this check fails with
    # AssertionError.
    assert "617565" not in goal and max_steps == 8
    # Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)
    # Assert that 'PASS' is in out AND 'Cited answer: 617565 [https://en.wikipedia.org/wiki/Boston]'
    # is in out. If false, this check fails with AssertionError.
    assert "PASS" in out and "Cited answer: 617565 [https://en.wikipedia.org/wiki/Boston]" in out


# Define test_demo_wrong_answer_fails_after_cleanup with parameters monkeypatch.
def test_demo_wrong_answer_fails_after_cleanup(monkeypatch):
    # Set events to run_demo(monkeypatch, answer='123456').
    events = run_demo(monkeypatch, answer="123456")
    # Use pytest.raises(SystemExit, match='does not contain'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(SystemExit, match="does not contain"):
        # Call runpy.run_path with SCRIPT converted to a string.
        runpy.run_path(str(SCRIPT), run_name="__main__")
    # Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)


# Define test_demo_rejects_finishing_on_unexpected_host with parameters monkeypatch.
def test_demo_rejects_finishing_on_unexpected_host(monkeypatch):
    # Call run_demo with monkeypatch.
    run_demo(monkeypatch, final_url="https://evil.com/")
    # Use pytest.raises(SystemExit, match='unexpected page'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(SystemExit, match="unexpected page"):
        # Call runpy.run_path with SCRIPT converted to a string.
        runpy.run_path(str(SCRIPT), run_name="__main__")


# Define test_demo_stops_before_model_calls_when_source_page_is_an_error with parameters
# monkeypatch.
def test_demo_stops_before_model_calls_when_source_page_is_an_error(monkeypatch):
    # Set events to run_demo(monkeypatch, article_count=0).
    events = run_demo(monkeypatch, article_count=0)
    # Use pytest.raises(SystemExit, match='SOURCE UNAVAILABLE.*Wikimedia Error.*No model calls');
    # leave the context and run its cleanup when this block ends.
    with pytest.raises(SystemExit, match="SOURCE UNAVAILABLE.*Wikimedia Error.*No model calls"):
        # Call runpy.run_path with SCRIPT converted to a string.
        runpy.run_path(str(SCRIPT), run_name="__main__")
    # Assert that not (any((event[0] == 'run' for event in events))). If false, this check fails
    # with AssertionError.
    assert not any(event[0] == "run" for event in events)
    # Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)


# Define test_demo_agent_failure_still_cleans_up with parameters monkeypatch.
def test_demo_agent_failure_still_cleans_up(monkeypatch):
    # Set events to run_demo(monkeypatch, failure=True).
    events = run_demo(monkeypatch, failure=True)
    # Use pytest.raises(RuntimeError, match='Vision failed'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(RuntimeError, match="Vision failed"):
        # Call runpy.run_path with SCRIPT converted to a string.
        runpy.run_path(str(SCRIPT), run_name="__main__")
    # Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)
