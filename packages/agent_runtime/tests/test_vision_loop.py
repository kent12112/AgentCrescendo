from contextlib import contextmanager
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from crescendo_agent.model import Entry
from crescendo_agent.vision import GroqVision, Screenshot
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import TaskGrant, ToolCall

GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())


class VisionScript:
    def __init__(self, calls):
        self.calls = iter(calls)
        self.seen = []
        self.images = []

    def decide(self, image, transcript):
        self.images.append(image)
        self.seen.append(list(transcript))
        return next(self.calls)


def test_vision_loop_denies_invalid_scroll_then_acts_and_observes_again():
    desktop = Mock()
    images = [Mock(size=(1024, 768)) for _ in range(3)]
    desktop.capture_screen.side_effect = images
    model = VisionScript([
        ToolCall("scroll", {"direction": "down", "amount": 100}),
        ToolCall("scroll", {"direction": "down", "amount": 3}),
        ToolCall("finish", {"answer": "Visual code ABC123"}),
    ])
    result = run_vision_agent("Read code below", GRANT, desktop, model)
    assert result.status == "finished"
    assert result.answer == "Visual code ABC123"
    assert len(result.denied) == 1
    desktop.scroll.assert_called_once_with("down", 3)
    assert model.images == images
    assert any(entry.kind == "denied" for entry in model.seen[1])
    assert any("scroll completed" in entry.text for entry in model.seen[2])


def test_bad_code_format_is_denied_and_model_can_retry_without_oracle():
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    validate = runpy.run_path(str(script))["validate_code_answer"]
    model = VisionScript([ToolCall("finish", {"answer": "visual=51,174"}),
                          ToolCall("finish", {"answer": "ABC123"})])
    screenshots = []
    desktop = Mock()
    result = run_vision_agent("Read the target code", GRANT, desktop, model,
                              finish_validator=validate,
                              on_screenshot=lambda step, image: screenshots.append((step, image)))
    assert result.status == "finished"
    assert result.answer == "ABC123"
    assert len(result.denied) == 1
    assert "six hexadecimal" in result.denied[0][1].reason
    assert "ABC123" not in result.denied[0][1].reason
    assert [step for step, image in screenshots] == [1, 2]
    assert [image for step, image in screenshots] == model.images
    assert any(entry.kind == "denied" for entry in model.seen[1])


def test_vision_loop_stops_repeated_scrolls_at_step_limit():
    desktop = Mock()
    model = VisionScript([ToolCall("scroll", {"direction": "down", "amount": 1})] * 3)
    result = run_vision_agent("Keep searching", GRANT, desktop, model, max_steps=3)
    assert result.status == "step_limit"
    assert desktop.scroll.call_count == 3
    assert desktop.capture_screen.call_count == 3


def test_vision_loop_does_not_execute_late_model_proposal():
    now = [0]
    desktop, model = Mock(), Mock()
    def decide(*args):
        now[0] = 121
        return ToolCall("scroll", {"direction": "down", "amount": 1})
    model.decide.side_effect = decide
    result = run_vision_agent("Find code", GRANT, desktop, model, clock=lambda: now[0])
    assert result.status == "deadline"
    desktop.scroll.assert_not_called()


@pytest.mark.parametrize("call", [ToolCall("click", {"x": 1, "y": 1}),
                                  ToolCall("finish", {"answer": " "}),
                                  ToolCall("scroll", {"direction": "down", "amount": True})])
def test_vision_loop_rejects_unsupported_and_invalid_actions(call):
    desktop = Mock()
    result = run_vision_agent("Find code", GRANT, desktop, VisionScript([call]), max_steps=1)
    assert result.status == "step_limit"
    assert len(result.denied) == 1
    desktop.scroll.assert_not_called()


def test_vision_scroll_requires_grant_even_when_model_proposes_it():
    desktop = Mock()
    grant = TaskGrant("no-scroll", frozenset({"screenshot", "finish"}), frozenset())
    result = run_vision_agent("Find code", grant, desktop,
                              VisionScript([ToolCall("scroll", {"direction": "down", "amount": 1})]), max_steps=1)
    assert len(result.denied) == 1
    desktop.scroll.assert_not_called()


@pytest.mark.parametrize("kwargs", [{"max_steps": 0}, {"max_steps": True}, {"max_steps": 11},
                                    {"deadline_seconds": 0}, {"deadline_seconds": float("inf")}])
def test_vision_limits_are_validated_before_capture(kwargs):
    desktop = Mock()
    with pytest.raises(ValueError):
        run_vision_agent("Find code", GRANT, desktop, Mock(), **kwargs)
    desktop.capture_screen.assert_not_called()


def response(name, args, reason="tool_calls"):
    return NS(choices=[NS(finish_reason=reason, message=NS(tool_calls=[
        NS(type="function", function=NS(name=name, arguments=json.dumps(args)))
    ]))])


def test_vision_proposals_use_one_current_image_and_structured_tools():
    import base64
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=")
    client = Mock()
    client.chat.completions.create.return_value = response("scroll", {"direction": "down", "amount": 2})
    call = GroqVision(client=client).decide(Screenshot(png), [Entry("goal", "Find code below")])
    assert call == ToolCall("scroll", {"direction": "down", "amount": 2})
    request = client.chat.completions.create.call_args.kwargs
    assert request["tool_choice"] == "required"
    assert request["parallel_tool_calls"] is False
    assert {tool["function"]["name"] for tool in request["tools"]} == {"scroll", "finish"}
    content = request["messages"][1]["content"]
    assert [block["type"] for block in content] == ["text", "image_url"]
    assert base64.b64decode(content[1]["image_url"]["url"].split(",")[1]) == png


@pytest.mark.parametrize("bad", [response("click", {}), response("finish", {"answer": ""}),
                                  response("scroll", {"amount": 3}), response("finish", [], "length"),
                                  NS(choices=[])])
def test_malformed_vision_proposals_fail_without_action(bad):
    client = Mock()
    client.chat.completions.create.return_value = bad
    with pytest.raises(ValueError):
        GroqVision(client=client).decide(NS(png=b"fixture"), [])


@pytest.mark.parametrize("failure", [False, True])
def test_agent_demo_cleans_up_and_does_not_put_expected_code_in_goal(monkeypatch, failure, capsys):
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    monkeypatch.setattr(sys, "argv", ["e2b_vision_agent_demo.py"])
    codes = iter(["abc123", "def456"])
    monkeypatch.setattr("secrets.token_hex", lambda n: next(codes))
    closed = []
    @contextmanager
    def open_desktop(grant):
        try:
            yield Mock()
        finally:
            closed.append(True)
    def run(goal, grant, desktop, model, **kwargs):
        assert "ABC123" not in goal and "DEF456" not in goal
        if failure:
            raise RuntimeError("Vision failed")
        return NS(status="finished", answer="DEF456", denied=[], transcript=[])
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: NS(model=name))
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    if failure:
        with pytest.raises(RuntimeError, match="Vision failed"):
            runpy.run_path(str(script), run_name="__main__")
    else:
        runpy.run_path(str(script), run_name="__main__")
        assert "PASS" in capsys.readouterr().out
    assert closed == [True]
