# Learn: From contextlib, import contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: Import runpy: use this module through its namespace.
import runpy
# Learn: Import sys: provides process details and standard input/output streams.
import sys
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.e2b_desktop, import SCROLL_POINTER (a dependency used below); E2BDesktop (a
# dependency used below).
from crescendo_agent.e2b_desktop import SCROLL_POINTER, E2BDesktop
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize (checks task
# grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Learn: Set GRANT to TaskGrant('scroll', frozenset({'scroll', 'screenshot'}), frozenset()).
GRANT = TaskGrant("scroll", frozenset({"scroll", "screenshot"}), frozenset())


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("args", [
    # Learn: Add this item to the surrounding list: {"direction": "down", "amount": 0}, {"direction": "up",
    # "amount": 6},.
    {"direction": "down", "amount": 0}, {"direction": "up", "amount": 6},
    # Learn: Add this item to the surrounding list: {"direction": "left", "amount": 1}, {"direction":
    # "down", "amount": True},.
    {"direction": "left", "amount": 1}, {"direction": "down", "amount": True},
    # Learn: Add this item to the surrounding list: {"direction": "down", "amount": "2"}, {"direction":
    # "down"},.
    {"direction": "down", "amount": "2"}, {"direction": "down"},
    # Learn: Add this item to the surrounding list: {"direction": "down", "amount": 1, "command": "extra"},.
    {"direction": "down", "amount": 1, "command": "extra"},
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test scroll arguments fail closed. pytest supplies named fixtures and checks assertions below.
def test_scroll_arguments_fail_closed(args):
    # Learn: Assert that not (authorize(GRANT, ToolCall('scroll', args)).allowed). If false, this check
    # fails with AssertionError.
    assert not authorize(GRANT, ToolCall("scroll", args)).allowed


# Learn: Test scroll requires explicit grant. pytest supplies named fixtures and checks assertions below.
def test_scroll_requires_explicit_grant():
    # Learn: Set (page, provider, pointer) to the tuple (Mock(), Mock(), Mock()) (positional values).
    page, provider, pointer = Mock(), Mock(), Mock()
    # Learn: Set desktop to E2BDesktop(page, Mock(), TaskGrant('no-scroll', frozenset(), frozenset()),
    # scroll_provider=provider, pointer_provider=pointer).
    desktop = E2BDesktop(page, Mock(), TaskGrant("no-scroll", frozenset(), frozenset()),
                         # Learn: Pass keyword scroll_provider = provider.
                         scroll_provider=provider, pointer_provider=pointer)
    # Learn: Enter pytest.raises(ValueError, match='not permitted'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(ValueError, match="not permitted"):
        # Learn: Execute the already-checked wheel action; the next screenshot shows its effect on desktop;
        # inputs: 'down', 1.
        desktop.scroll("down", 1)
    # Learn: Verify the denied/error path never invoked this fake dependency on provider.
    provider.assert_not_called()
    # Learn: Verify the denied/error path never invoked this fake dependency on pointer.
    pointer.assert_not_called()
    # Learn: Verify the denied/error path never invoked this fake dependency on page.bring_to_front.
    page.bring_to_front.assert_not_called()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("direction,amount", [("up", 1), ("down", 5)])
# Learn: Test authorized scroll moves real pointer before wheel. pytest supplies named fixtures and checks
# assertions below.
def test_authorized_scroll_moves_real_pointer_before_wheel(direction, amount):
    # Learn: Set (page, pointer) to the tuple (Mock(), Mock()) (positional values).
    page, pointer = Mock(), Mock()
    # Learn: Define provider(). The body runs when called, not when defined.
    def provider(**kwargs):
        # Learn: Verify the fake dependency ran exactly once with these arguments on page.bring_to_front.
        page.bring_to_front.assert_called_once_with()
        # The real desktop pointer, not Playwright's synthetic mouse, must be placed first.
        # Learn: Verify the fake dependency ran exactly once with these arguments on pointer; inputs:
        # *SCROLL_POINTER.
        pointer.assert_called_once_with(*SCROLL_POINTER)
        # Learn: Assert that kwargs equals a new dictionary with keys 'direction', 'amount'. If false, this
        # check fails with AssertionError.
        assert kwargs == {"direction": direction, "amount": amount}
    # Learn: Set wrapped to Mock(side_effect=provider).
    wrapped = Mock(side_effect=provider)
    # Learn: Set desktop to E2BDesktop(page, Mock(), GRANT, scroll_provider=wrapped,
    # pointer_provider=pointer).
    desktop = E2BDesktop(page, Mock(), GRANT, scroll_provider=wrapped, pointer_provider=pointer)
    # Learn: Execute the already-checked wheel action; the next screenshot shows its effect on desktop;
    # inputs: direction, amount.
    desktop.scroll(direction, amount)
    # Learn: Verify the fake dependency ran exactly once with these arguments on wrapped.
    wrapped.assert_called_once_with(direction=direction, amount=amount)
    # Learn: Verify the denied/error path never invoked this fake dependency on page.mouse.move.
    page.mouse.move.assert_not_called()


# Learn: Test scroll point is inside page area of e2b display. pytest supplies named fixtures and checks
# assertions below.
def test_scroll_point_is_inside_page_area_of_e2b_display():
    # Learn: Set (x, y) to SCROLL_POINTER.
    x, y = SCROLL_POINTER
    # Learn: Assert that 0 is less than x is less than 1024 AND 114 is less than y is less than 768. If
    # false, this check fails with AssertionError.
    assert 0 < x < 1024 and 114 < y < 768


# Learn: Test scroll without pointer provider fails closed. pytest supplies named fixtures and checks
# assertions below.
def test_scroll_without_pointer_provider_fails_closed():
    # Learn: Set provider to Mock().
    provider = Mock()
    # Learn: Set desktop to E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider).
    desktop = E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider)
    # Learn: Enter pytest.raises(RuntimeError, match='pointer'). The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="pointer"):
        # Learn: Execute the already-checked wheel action; the next screenshot shows its effect on desktop;
        # inputs: 'down', 1.
        desktop.scroll("down", 1)
    # Learn: Verify the denied/error path never invoked this fake dependency on provider.
    provider.assert_not_called()


# Learn: Test invalid scroll never reaches provider. pytest supplies named fixtures and checks assertions
# below.
def test_invalid_scroll_never_reaches_provider():
    # Learn: Set (provider, pointer) to the tuple (Mock(), Mock()) (positional values).
    provider, pointer = Mock(), Mock()
    # Learn: Set desktop to E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider,
    # pointer_provider=pointer).
    desktop = E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider, pointer_provider=pointer)
    # Learn: Enter pytest.raises(ValueError, match='1 to 5'). The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with pytest.raises(ValueError, match="1 to 5"):
        # Learn: Execute the already-checked wheel action; the next screenshot shows its effect on desktop;
        # inputs: 'down', 100.
        desktop.scroll("down", 100)
    # Learn: Verify the denied/error path never invoked this fake dependency on provider.
    provider.assert_not_called()
    # Learn: Verify the denied/error path never invoked this fake dependency on pointer.
    pointer.assert_not_called()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("second_call_fails", [False, True])
# Learn: Test scroll demo order and cleanup. pytest supplies named fixtures and checks assertions below.
def test_scroll_demo_order_and_cleanup(monkeypatch, capsys, second_call_fails):
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'E2B_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'GROQ_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr(sys, "argv", ["e2b_vision_demo.py", "--scroll"])
    # Learn: Set codes to iter(['abc123', 'def456']).
    codes = iter(["abc123", "def456"])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("secrets.token_hex", lambda n: next(codes))
    # Learn: Set events to a new list (empty).
    events = []
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set desktop.capture_screen.side_effect to lambda : events.append('capture') or Mock(size=(1024,
    # 768)).
    desktop.capture_screen.side_effect = lambda: events.append("capture") or Mock(size=(1024, 768))
    # Learn: Set desktop.scroll.side_effect to lambda *args: events.append('scroll').
    desktop.scroll.side_effect = lambda *args: events.append("scroll")

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Learn: Define fake_open(grant). The body runs when called, not when defined.
    def fake_open(grant):
        # Learn: Assert that grant.allowed_tools equals frozenset({'scroll', 'screenshot'}). If false, this
        # check fails with AssertionError.
        assert grant.allowed_tools == frozenset({"scroll", "screenshot"})
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Yield desktop to the with-block/request; resume here for cleanup afterward.
            yield desktop
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Append one item to the ordered collection on events; inputs: 'cleanup'.
            events.append("cleanup")

    # Learn: Set model to Mock(model='test-model'); the provider adapter or scripted test model used to
    # propose actions.
    model = Mock(model="test-model")
    # Learn: Define describe(image). The body runs when called, not when defined.
    def describe(image):
        # Learn: Append one item to the ordered collection on events; inputs: 'describe'.
        events.append("describe")
        # Learn: Take this branch only if events.count('describe') equals 1.
        if events.count("describe") == 1:
            # Learn: Return 'Visual code: ABC123' to the caller and stop this function.
            return "Visual code: ABC123"
        # Learn: Take this branch only if second_call_fails.
        if second_call_fails:
            # Learn: Raise RuntimeError('Vision unavailable') to stop the normal path.
            raise RuntimeError("Vision unavailable")
        # Learn: Return 'Visual code: DEF456' to the caller and stop this function.
        return "Visual code: DEF456"
    # Learn: Set model.describe.side_effect to describe.
    model.describe.side_effect = describe
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: model)
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_demo.py"
    # Learn: Take this branch only if second_call_fails.
    if second_call_fails:
        # Learn: Enter pytest.raises(RuntimeError, match='Vision unavailable'). The context manager controls
        # setup/exit; inspect it for the actual cleanup behavior.
        with pytest.raises(RuntimeError, match="Vision unavailable"):
            # Learn: Call runpy.run_path with the arguments shown.
            runpy.run_path(str(script), run_name="__main__")
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(script), run_name="__main__")
    # Learn: Assert that events equals a new list containing 'capture', 'describe', 'scroll', 'capture',
    # 'describe', 'cleanup'. If false, this check fails with AssertionError.
    assert events == ["capture", "describe", "scroll", "capture", "describe", "cleanup"]
    # Learn: Verify the fake dependency ran exactly once with these arguments on desktop.scroll; inputs:
    # 'down', 5.
    desktop.scroll.assert_called_once_with("down", 5)
    # Learn: Take this branch only if not (second_call_fails).
    if not second_call_fails:
        # Learn: Assert that 'PASS: one bounded scroll' is in capsys.readouterr().out. If false, this check
        # fails with AssertionError.
        assert "PASS: one bounded scroll" in capsys.readouterr().out
