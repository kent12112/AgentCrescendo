from contextlib import contextmanager
from pathlib import Path
import runpy
import sys
from unittest.mock import Mock

import pytest

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_security.policy import TaskGrant, ToolCall, authorize

GRANT = TaskGrant("scroll", frozenset({"scroll", "screenshot"}), frozenset())


@pytest.mark.parametrize("args", [
    {"direction": "down", "amount": 0}, {"direction": "up", "amount": 6},
    {"direction": "left", "amount": 1}, {"direction": "down", "amount": True},
    {"direction": "down", "amount": "2"}, {"direction": "down"},
    {"direction": "down", "amount": 1, "command": "extra"},
])
def test_scroll_arguments_fail_closed(args):
    assert not authorize(GRANT, ToolCall("scroll", args)).allowed


def test_scroll_requires_explicit_grant():
    page, provider = Mock(), Mock()
    desktop = E2BDesktop(page, Mock(), TaskGrant("no-scroll", frozenset(), frozenset()), scroll_provider=provider)
    with pytest.raises(ValueError, match="not permitted"):
        desktop.scroll("down", 1)
    provider.assert_not_called()
    page.bring_to_front.assert_not_called()
    page.mouse.move.assert_not_called()


@pytest.mark.parametrize("direction,amount", [("up", 1), ("down", 5)])
def test_authorized_scroll_targets_content_and_calls_provider_once(direction, amount):
    page = Mock()
    def provider(**kwargs):
        page.bring_to_front.assert_called_once_with()
        page.mouse.move.assert_called_once_with(200, 200)
        assert kwargs == {"direction": direction, "amount": amount}
    wrapped = Mock(side_effect=provider)
    desktop = E2BDesktop(page, Mock(), GRANT, scroll_provider=wrapped)
    desktop.scroll(direction, amount)
    wrapped.assert_called_once_with(direction=direction, amount=amount)


def test_invalid_scroll_never_reaches_provider():
    provider = Mock()
    desktop = E2BDesktop(Mock(), Mock(), GRANT, scroll_provider=provider)
    with pytest.raises(ValueError, match="1 to 5"):
        desktop.scroll("down", 100)
    provider.assert_not_called()


@pytest.mark.parametrize("second_call_fails", [False, True])
def test_scroll_demo_order_and_cleanup(monkeypatch, capsys, second_call_fails):
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    monkeypatch.setattr(sys, "argv", ["e2b_vision_demo.py", "--scroll"])
    codes = iter(["abc123", "def456"])
    monkeypatch.setattr("secrets.token_hex", lambda n: next(codes))
    events = []
    desktop = Mock()
    desktop.capture_screen.side_effect = lambda: events.append("capture") or Mock(size=(1024, 768))
    desktop.scroll.side_effect = lambda *args: events.append("scroll")

    @contextmanager
    def fake_open(grant):
        assert grant.allowed_tools == frozenset({"scroll", "screenshot"})
        try:
            yield desktop
        finally:
            events.append("cleanup")

    model = Mock(model="test-model")
    def describe(image):
        events.append("describe")
        if events.count("describe") == 1:
            return "Visual code: ABC123"
        if second_call_fails:
            raise RuntimeError("Vision unavailable")
        return "Visual code: DEF456"
    model.describe.side_effect = describe
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: model)
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_demo.py"
    if second_call_fails:
        with pytest.raises(RuntimeError, match="Vision unavailable"):
            runpy.run_path(str(script), run_name="__main__")
    else:
        runpy.run_path(str(script), run_name="__main__")
    assert events == ["capture", "describe", "scroll", "capture", "describe", "cleanup"]
    desktop.scroll.assert_called_once_with("down", 5)
    if not second_call_fails:
        assert "PASS: one bounded scroll" in capsys.readouterr().out
