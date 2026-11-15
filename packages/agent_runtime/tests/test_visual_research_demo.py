# Learn: From contextlib, import contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: Import runpy: use this module through its namespace.
import runpy
# Learn: Import sys: provides process details and standard input/output streams.
import sys
# Learn: From types, import SimpleNamespace as NS (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace as NS
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.model, import Entry (represents one typed transcript item sent to the model).
from crescendo_agent.model import Entry

# Learn: Set SCRIPT to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
# 'e2b_visual_research_demo.py'.
SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "e2b_visual_research_demo.py"
# Learn: Set DEMO to runpy.run_path(str(SCRIPT)).
DEMO = runpy.run_path(str(SCRIPT))


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("answer,page_text,visible,passed,reason", [
    # Learn: Add this item to the surrounding list: ("617565", "GNIS feature ID 617565", True, True,
    # "PASS"),.
    ("617565", "GNIS feature ID 617565", True, True, "PASS"),
    # Learn: Add this item to the surrounding list: ("617565", "GNIS feature ID 999999", True, False,
    # "FIXTURE CHANGED"),.
    ("617565", "GNIS feature ID 999999", True, False, "FIXTURE CHANGED"),
    # Learn: Add this item to the surrounding list: ("617566", "GNIS feature ID 617565", True, False, "does
    # not contain"),.
    ("617566", "GNIS feature ID 617565", True, False, "does not contain"),
    # Learn: Add this item to the surrounding list: (None, "GNIS feature ID 617565", True, False, "does not
    # contain"),.
    (None, "GNIS feature ID 617565", True, False, "does not contain"),
    # Correct value but not on screen at finish: could be memorized or guessed, not seen.
    # Learn: Add this item to the surrounding list: ("617565", "GNIS feature ID 617565", False, False, "not
    # on screen"),.
    ("617565", "GNIS feature ID 617565", False, False, "not on screen"),
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test grade requires correct supported and visible. pytest supplies named fixtures and checks
# assertions below.
def test_grade_requires_correct_supported_and_visible(answer, page_text, visible, passed, reason):
    # Learn: Set (ok, message) to DEMO['grade'](answer, '617565', page_text, visible).
    ok, message = DEMO["grade"](answer, "617565", page_text, visible)
    # Learn: Assert that ok is passed. If false, this check fails with AssertionError.
    assert ok is passed
    # Learn: Assert that reason is in message. If false, this check fails with AssertionError.
    assert reason in message


# Learn: Test short answer validator. pytest supplies named fixtures and checks assertions below.
def test_short_answer_validator():
    # Learn: Assert that DEMO['validate_short_answer']('617565') is None (no value). If false, this check
    # fails with AssertionError.
    assert DEMO["validate_short_answer"]("617565") is None
    # Learn: Assert that '200 characters' is in DEMO['validate_short_answer']('x' * 201). If false, this
    # check fails with AssertionError.
    assert "200 characters" in DEMO["validate_short_answer"]("x" * 201)


# Learn: Test model tools lists only proposed actions. pytest supplies named fixtures and checks assertions
# below.
def test_model_tools_lists_only_proposed_actions():
    # Learn: Set transcript to a new list containing Entry('goal', 'g'), Entry('observation', 'o'),
    # Entry('action', '{"tool": "scroll", "args": {}}'), Entry('denied', 'no'), Entry('acti...; the ordered
    # goal, observation, proposal, and denial history.
    transcript = [Entry("goal", "g"), Entry("observation", "o"),
                  # Learn: Call Entry with the arguments shown.
                  Entry("action", '{"tool": "scroll", "args": {}}'), Entry("denied", "no"),
                  # Learn: Call Entry with the arguments shown.
                  Entry("action", '{"tool": "finish", "args": {}}')]
    # Learn: Assert that DEMO['model_tools'](transcript) equals a new list containing 'scroll', 'finish'. If
    # false, this check fails with AssertionError.
    assert DEMO["model_tools"](transcript) == ["scroll", "finish"]


# Learn: Test decision lines show reason or placeholder. pytest supplies named fixtures and checks
# assertions below.
def test_decision_lines_show_reason_or_placeholder():
    # Learn: Set transcript to a new list containing Entry('action', '{"tool": "scroll", "args":
    # {"direction": "down", "amount": 5}, "reason": "Infobox continues below"}'), Entry('actio...; the
    # ordered goal, observation, proposal, and denial history.
    transcript = [Entry("action", '{"tool": "scroll", "args": {"direction": "down", "amount": 5}, '
                                  # Learn: Supply the next argument to Entry: '"reason": "Infobox continues
                                  # below"}'),.
                                  '"reason": "Infobox continues below"}'),
                  # Learn: Call Entry with the arguments shown.
                  Entry("action", '{"tool": "finish", "args": {"answer": "617565"}}')]
    # Learn: Assert that DEMO['decision_lines'](transcript) equals a new list containing " 1.
    # scroll(direction='down', amount=5) — reason: 'Infobox continues below'", " 2. finish(answer='617565')
    # — reason: '(none given)'". If false, this check fails with AssertionError.
    assert DEMO["decision_lines"](transcript) == [
        # Learn: Supply literal text " 1. scroll(direction='down', amount=5) — reason: 'Infobox continues
        # below'"; adjacent string literals are concatenated without adding whitespace.
        "  1. scroll(direction='down', amount=5) — reason: 'Infobox continues below'",
        # Learn: Supply literal text " 2. finish(answer='617565') — reason: '(none given)'"; adjacent string
        # literals are concatenated without adding whitespace.
        "  2. finish(answer='617565') — reason: '(none given)'",
    # Learn: Close this list literal; delimiters group the values into one object.
    ]


# Learn: Define run_demo(monkeypatch, answer, final_url, failure, article_count). The body runs when called,
# not when defined.
def run_demo(monkeypatch, *, answer="617565", final_url=None, failure=False, article_count=1):
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'E2B_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'GROQ_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr(sys, "argv", ["e2b_visual_research_demo.py"])
    # Learn: Set events to a new list (empty).
    events = []
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set desktop.page.url to final_url OR DEMO['SOURCE_URL']; the destination or current page
    # address.
    desktop.page.url = final_url or DEMO["SOURCE_URL"]
    # Learn: Set desktop.page.evaluate.return_value to True.
    desktop.page.evaluate.return_value = True
    # Learn: Set desktop.page.locator.return_value.inner_text.return_value to 'GNIS feature ID 617565'.
    desktop.page.locator.return_value.inner_text.return_value = "GNIS feature ID 617565"
    # Learn: Set desktop.page.locator.return_value.count.return_value to article_count.
    desktop.page.locator.return_value.count.return_value = article_count
    # Learn: Set desktop.page.title.return_value to 'Wikimedia Error'.
    desktop.page.title.return_value = "Wikimedia Error"
    # Learn: Set desktop.blocked_requests to a new list (empty); the browser requests rejected by the
    # request filter.
    desktop.blocked_requests = []
    # Learn: Set desktop.navigate.side_effect to lambda url: events.append(('navigate', url)).
    desktop.navigate.side_effect = lambda url: events.append(("navigate", url))

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Learn: Define open_desktop(grant, lifetime_seconds). The body runs when called, not when defined.
    def open_desktop(grant, *, lifetime_seconds):
        # Learn: Assert that lifetime_seconds equals 300. If false, this check fails with AssertionError.
        assert lifetime_seconds == 300
        # Learn: Append one item to the ordered collection on events; inputs: the tuple ('open', grant)
        # (positional values).
        events.append(("open", grant))
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Yield desktop to the with-block/request; resume here for cleanup afterward.
            yield desktop
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Append one item to the ordered collection on events; inputs: the tuple ('closed',)
            # (positional values).
            events.append(("closed",))

    # Learn: Define run(goal, grant, desk, model). The body runs when called, not when defined.
    def run(goal, grant, desk, model, **kwargs):
        # Learn: Append one item to the ordered collection on events; inputs: the tuple ('run', goal,
        # kwargs['max_steps']) (positional values).
        events.append(("run", goal, kwargs["max_steps"]))
        # Learn: Take this branch only if failure.
        if failure:
            # Learn: Raise RuntimeError('Vision failed') to stop the normal path.
            raise RuntimeError("Vision failed")
        # Learn: Return NS(status='finished', answer=answer, denied=[], transcript=[Entry('action',
        # '{"tool": "scroll", "args": {}}'), Entry('action', '{"to... to the caller and stop this function.
        return NS(status="finished", answer=answer, denied=[],
                  # Learn: Pass keyword transcript = a new list containing Entry('action', '{"tool":
                  # "scroll", "args": {}}'), Entry('action', '{"tool": "finish", "args": {}}').
                  transcript=[Entry("action", '{"tool": "scroll", "args": {}}'),
                              # Learn: Call Entry with the arguments shown.
                              Entry("action", '{"tool": "finish", "args": {}}')])

    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: NS(model=name))
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    # Learn: Return events to the caller and stop this function.
    return events


# Learn: Test demo navigates first hides expected value and cleans up. pytest supplies named fixtures and
# checks assertions below.
def test_demo_navigates_first_hides_expected_value_and_cleans_up(monkeypatch, capsys):
    # Learn: Set events to run_demo(monkeypatch).
    events = run_demo(monkeypatch)
    # Learn: Call runpy.run_path with the arguments shown.
    runpy.run_path(str(SCRIPT), run_name="__main__")
    # Learn: Set out to capsys.readouterr().out.
    out = capsys.readouterr().out
    # Learn: Set grant to events[0][1]; the task identity and fixed tool/host permissions; model output
    # cannot expand these.
    grant = events[0][1]
    # Learn: Assert that grant.allowed_hosts equals frozenset({'en.wikipedia.org'}). If false, this check
    # fails with AssertionError.
    assert grant.allowed_hosts == frozenset({"en.wikipedia.org"})
    # Learn: Assert that 'click' is not in grant.allowed_tools. If false, this check fails with
    # AssertionError.
    assert "click" not in grant.allowed_tools
    # Learn: Assert that events[1] equals the tuple ('navigate', DEMO['SOURCE_URL']) (positional values). If
    # false, this check fails with AssertionError.
    assert events[1] == ("navigate", DEMO["SOURCE_URL"])
    # Learn: Set (_, goal, max_steps) to events[2].
    _, goal, max_steps = events[2]
    # Learn: Assert that '617565' is not in goal AND max_steps equals 8. If false, this check fails with
    # AssertionError.
    assert "617565" not in goal and max_steps == 8
    # Learn: Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)
    # Learn: Assert that 'PASS' is in out AND 'Cited answer: 617565 [https://en.wikipedia.org/wiki/Boston]'
    # is in out. If false, this check fails with AssertionError.
    assert "PASS" in out and "Cited answer: 617565 [https://en.wikipedia.org/wiki/Boston]" in out


# Learn: Test demo wrong answer fails after cleanup. pytest supplies named fixtures and checks assertions
# below.
def test_demo_wrong_answer_fails_after_cleanup(monkeypatch):
    # Learn: Set events to run_demo(monkeypatch, answer='123456').
    events = run_demo(monkeypatch, answer="123456")
    # Learn: Enter pytest.raises(SystemExit, match='does not contain'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(SystemExit, match="does not contain"):
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(SCRIPT), run_name="__main__")
    # Learn: Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)


# Learn: Test demo rejects finishing on unexpected host. pytest supplies named fixtures and checks
# assertions below.
def test_demo_rejects_finishing_on_unexpected_host(monkeypatch):
    # Learn: Call run_demo with the arguments shown.
    run_demo(monkeypatch, final_url="https://evil.com/")
    # Learn: Enter pytest.raises(SystemExit, match='unexpected page'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(SystemExit, match="unexpected page"):
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(SCRIPT), run_name="__main__")


# Learn: Test demo stops before model calls when source page is an error. pytest supplies named fixtures and
# checks assertions below.
def test_demo_stops_before_model_calls_when_source_page_is_an_error(monkeypatch):
    # Learn: Set events to run_demo(monkeypatch, article_count=0).
    events = run_demo(monkeypatch, article_count=0)
    # Learn: Enter pytest.raises(SystemExit, match='SOURCE UNAVAILABLE.*Wikimedia Error.*No model calls').
    # The context manager controls setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(SystemExit, match="SOURCE UNAVAILABLE.*Wikimedia Error.*No model calls"):
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(SCRIPT), run_name="__main__")
    # Learn: Assert that not (any((event[0] == 'run' for event in events))). If false, this check fails with
    # AssertionError.
    assert not any(event[0] == "run" for event in events)
    # Learn: Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)


# Learn: Test demo agent failure still cleans up. pytest supplies named fixtures and checks assertions
# below.
def test_demo_agent_failure_still_cleans_up(monkeypatch):
    # Learn: Set events to run_demo(monkeypatch, failure=True).
    events = run_demo(monkeypatch, failure=True)
    # Learn: Enter pytest.raises(RuntimeError, match='Vision failed'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="Vision failed"):
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(SCRIPT), run_name="__main__")
    # Learn: Assert that events[-1] equals the tuple ('closed',) (positional values). If false, this check
    # fails with AssertionError.
    assert events[-1] == ("closed",)
