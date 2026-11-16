# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import runpy: use this module through its namespace.
import runpy
# Import sys: provides process details and standard input/output streams.
import sys
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.e2b_desktop: SCROLL_POINTER (a dependency used below); E2BDesktop (a
# dependency used below).
from crescendo_agent.e2b_desktop import SCROLL_POINTER, E2BDesktop
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize
# (checks task grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Set GRANT to TaskGrant('scroll', frozenset({'scroll', 'screenshot'}), frozenset()).
GRANT = TaskGrant("scroll", frozenset({"scroll", "screenshot"}), frozenset())


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("args", [
    # Add this item to the surrounding list: {"direction": "down", "amount": 0}, {"direction": "up",
    # "amount": 6},.
    {"direction": "down", "amount": 0}, {"direction": "up", "amount": 6},
    # Add this item to the surrounding list: {"direction": "left", "amount": 1}, {"direction":
    # "down", "amount": True},.
    {"direction": "left", "amount": 1}, {"direction": "down", "amount": True},
    # Add this item to the surrounding list: {"direction": "down", "amount": "2"}, {"direction":
    # "down"},.
    {"direction": "down", "amount": "2"}, {"direction": "down"},
    # Add this item to the surrounding list: {"direction": "down", "amount": 1, "command":
    # "extra"},.
    {"direction": "down", "amount": 1, "command": "extra"},
])
# Define test_scroll_arguments_fail_closed with parameters args.
def test_scroll_arguments_fail_closed(args):
    # Assert that not (authorize(GRANT, ToolCall('scroll', args)).allowed). If false, this check
    # fails with AssertionError.
    assert not authorize(GRANT, ToolCall("scroll", args)).allowed


# Define test_scroll_requires_explicit_grant with no parameters.
def test_scroll_requires_explicit_grant():
    # Set (page, provider, pointer) to (Mock(), Mock(), Mock()).
    page, provider, pointer = Mock(), Mock(), Mock()
    # Set desktop to E2BDesktop(page, Mock(), TaskGrant('no-scroll', frozenset(), frozenset()),
    # scroll_provider=provider, pointer_provider=pointer).
    desktop = E2BDesktop(page, Mock(), TaskGrant("no-scroll", frozenset(), frozenset()),
                         # Pass keyword scroll_provider = provider.
                         scroll_provider=provider, pointer_provider=pointer)
    # Use pytest.raises(ValueError, match='not permitted'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(ValueError, match="not permitted"):
        # Call desktop.scroll with 'down', 1.
        desktop.scroll("down", 1)
    # Call provider.assert_not_called with no arguments.
    provider.assert_not_called()
    # Call pointer.assert_not_called with no arguments.
    pointer.assert_not_called()
    # Call page.bring_to_front.assert_not_called with no arguments.
    page.bring_to_front.assert_not_called()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("direction,amount", [("up", 1), ("down", 5)])
# Define test_authorized_scroll_moves_real_pointer_before_wheel with parameters direction, amount.
def test_authorized_scroll_moves_real_pointer_before_wheel(direction, amount):
    # Set (page, pointer) to (Mock(), Mock()).
    page, pointer = Mock(), Mock()
    # Define provider with no parameters.
    def provider(**kwargs):
        # Call page.bring_to_front.assert_called_once_with with no arguments.
        page.bring_to_front.assert_called_once_with()
        # The real desktop pointer, not Playwright's synthetic mouse, must be placed first.
        # Call pointer.assert_called_once_with with *SCROLL_POINTER.
        pointer.assert_called_once_with(*SCROLL_POINTER)
        # Assert that kwargs equals a new dictionary with keys 'direction', 'amount'. If false, this
        # check fails with AssertionError.
        assert kwargs == {"direction": direction, "amount": amount}
    # Set wrapped to Mock(side_effect=provider).
    wrapped = Mock(side_effect=provider)
    # Set desktop to E2BDesktop(page, Mock(), GRANT, scroll_provider=wrapped,
    # pointer_provider=pointer).
    desktop = E2BDesktop(page, Mock(), GRANT, scroll_provider=wrapped, pointer_provider=pointer)
    # Call desktop.scroll with direction, amount.
    desktop.scroll(direction, amount)
    # Call wrapped.assert_called_once_with with no arguments.
    wrapped.assert_called_once_with(direction=direction, amount=amount)
    # Call page.mouse.move.assert_not_called with no arguments.
    page.mouse.move.assert_not_called()


# Define test_scroll_point_is_inside_page_area_of_e2b_display with no parameters.
def test_scroll_point_is_inside_page_area_of_e2b_display():
    # Set (x, y) to SCROLL_POINTER.
    x, y = SCROLL_POINTER
    # Assert that 0 is less than x is less than 1024 AND 114 is less than y is less than 768. If
    # false, this check fails with AssertionError.
    assert 0 < x < 1024 and 114 < y < 768


# Define test_scroll_without_pointer_provider_fails_closed with no parameters.
def test_scroll_without_pointer_provider_fails_closed():
    # Set provider to Mock().
    provider = Mock()
    # Set desktop to E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider).
    desktop = E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider)
    # Use pytest.raises(RuntimeError, match='pointer'); leave the context and run its cleanup when
    # this block ends.
    with pytest.raises(RuntimeError, match="pointer"):
        # Call desktop.scroll with 'down', 1.
        desktop.scroll("down", 1)
    # Call provider.assert_not_called with no arguments.
    provider.assert_not_called()


# Define test_invalid_scroll_never_reaches_provider with no parameters.
def test_invalid_scroll_never_reaches_provider():
    # Set (provider, pointer) to (Mock(), Mock()).
    provider, pointer = Mock(), Mock()
    # Set desktop to E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider,
    # pointer_provider=pointer).
    desktop = E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider, pointer_provider=pointer)
    # Use pytest.raises(ValueError, match='1 to 5'); leave the context and run its cleanup when this
    # block ends.
    with pytest.raises(ValueError, match="1 to 5"):
        # Call desktop.scroll with 'down', 100.
        desktop.scroll("down", 100)
    # Call provider.assert_not_called with no arguments.
    provider.assert_not_called()
    # Call pointer.assert_not_called with no arguments.
    pointer.assert_not_called()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("second_call_fails", [False, True])
# Define test_scroll_demo_order_and_cleanup with parameters monkeypatch, capsys, second_call_fails.
def test_scroll_demo_order_and_cleanup(monkeypatch, capsys, second_call_fails):
    # Call monkeypatch.setenv with 'E2B_API_KEY', 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Call monkeypatch.setenv with 'GROQ_API_KEY', 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Call monkeypatch.setattr with sys, 'argv', ['e2b_vision_demo.py', '--scroll'].
    monkeypatch.setattr(sys, "argv", ["e2b_vision_demo.py", "--scroll"])
    # Set codes to iter(['abc123', 'def456']).
    codes = iter(["abc123", "def456"])
    # Call monkeypatch.setattr with 'secrets.token_hex', a function that returns next(codes) when
    # called.
    monkeypatch.setattr("secrets.token_hex", lambda n: next(codes))
    # Set events to an empty list.
    events = []
    # Set desktop to Mock().
    desktop = Mock()
    # Set desktop.capture_screen.side_effect to a function that returns events.append('capture') or
    # Mock(size=(1024, 768)) when called.
    desktop.capture_screen.side_effect = lambda: events.append("capture") or Mock(size=(1024, 768))
    # Set desktop.scroll.side_effect to a function that returns events.append('scroll') when called.
    desktop.scroll.side_effect = lambda *args: events.append("scroll")

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define fake_open with parameters grant.
    def fake_open(grant):
        # Assert that grant.allowed_tools equals frozenset({'scroll', 'screenshot'}). If false, this
        # check fails with AssertionError.
        assert grant.allowed_tools == frozenset({"scroll", "screenshot"})
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give desktop to the caller and pause here until execution resumes.
            yield desktop
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Append 'cleanup' to events.
            events.append("cleanup")

    # Set model to Mock(model='test-model').
    model = Mock(model="test-model")
    # Define describe with parameters image.
    def describe(image):
        # Append 'describe' to events.
        events.append("describe")
        # Check whether events.count('describe') equals 1.
        if events.count("describe") == 1:
            # Return 'Visual code: ABC123'.
            return "Visual code: ABC123"
        # Check whether second_call_fails.
        if second_call_fails:
            # Raise RuntimeError('Vision unavailable') to stop the normal path.
            raise RuntimeError("Vision unavailable")
        # Return 'Visual code: DEF456'.
        return "Visual code: DEF456"
    # Set model.describe.side_effect to describe.
    model.describe.side_effect = describe
    # Call monkeypatch.setattr with 'crescendo_agent.e2b_desktop.open_e2b_desktop', fake_open.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    # Call monkeypatch.setattr with 'crescendo_agent.vision.GroqVision', a function that returns
    # model when called.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: model)
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_demo.py"
    # Check whether second_call_fails.
    if second_call_fails:
        # Use pytest.raises(RuntimeError, match='Vision unavailable'); leave the context and run its
        # cleanup when this block ends.
        with pytest.raises(RuntimeError, match="Vision unavailable"):
            # Call runpy.run_path with script converted to a string.
            runpy.run_path(str(script), run_name="__main__")
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Call runpy.run_path with script converted to a string.
        runpy.run_path(str(script), run_name="__main__")
    # Assert that events equals a new list containing 'capture', 'describe', 'scroll', 'capture',
    # 'describe', 'cleanup'. If false, this check fails with AssertionError.
    assert events == ["capture", "describe", "scroll", "capture", "describe", "cleanup"]
    # Call desktop.scroll.assert_called_once_with with 'down', 5.
    desktop.scroll.assert_called_once_with("down", 5)
    # Check whether not (second_call_fails).
    if not second_call_fails:
        # Assert that 'PASS: one bounded scroll' is in capsys.readouterr().out. If false, this check
        # fails with AssertionError.
        assert "PASS: one bounded scroll" in capsys.readouterr().out
