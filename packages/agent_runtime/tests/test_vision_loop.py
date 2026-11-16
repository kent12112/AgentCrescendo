# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
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
# Import from crescendo_agent.vision: GroqVision (adapts screenshot observations to Groq vision
# requests); Screenshot (validates the PNG container and dimensions at the image boundary).
from crescendo_agent.vision import GroqVision, Screenshot
# Import from crescendo_agent.vision_loop: run_vision_agent (runs the bounded
# screenshot/proposal/authorization/action loop).
from crescendo_agent.vision_loop import run_vision_agent
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall

# Set GRANT to TaskGrant('vision', frozenset({'screenshot', 'scroll', 'finish'}), frozenset()).
GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())


# Define VisionScript.
class VisionScript:
    # Define __init__ with parameters self, calls.
    def __init__(self, calls):
        # Set self.calls to iter(calls).
        self.calls = iter(calls)
        # Set self.seen to an empty list.
        self.seen = []
        # Set self.images to an empty list.
        self.images = []

    # Define decide with parameters self, image, transcript.
    def decide(self, image, transcript):
        # Append image to self.images.
        self.images.append(image)
        # Append list(transcript) to self.seen.
        self.seen.append(list(transcript))
        # Return next(self.calls).
        return next(self.calls)


# Define test_vision_loop_denies_invalid_scroll_then_acts_and_observes_again with no parameters.
def test_vision_loop_denies_invalid_scroll_then_acts_and_observes_again():
    # Set desktop to Mock().
    desktop = Mock()
    # Set images to [Mock(size=(1024, 768)) for _ in range(3)].
    images = [Mock(size=(1024, 768)) for _ in range(3)]
    # Set desktop.capture_screen.side_effect to images.
    desktop.capture_screen.side_effect = images
    # Set model to the result of VisionScript using the arguments below.
    model = VisionScript([
        # Call ToolCall with the arguments shown.
        ToolCall("scroll", {"direction": "down", "amount": 100}),
        # Call ToolCall with the arguments shown.
        ToolCall("scroll", {"direction": "down", "amount": 3}),
        # Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "Visual code ABC123"}),
    ])
    # Set result to run_vision_agent('Read code below', GRANT, desktop, model).
    result = run_vision_agent("Read code below", GRANT, desktop, model)
    # Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Assert that result.answer equals 'Visual code ABC123'. If false, this check fails with
    # AssertionError.
    assert result.answer == "Visual code ABC123"
    # Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Call desktop.scroll.assert_called_once_with with 'down', 3.
    desktop.scroll.assert_called_once_with("down", 3)
    # Assert that model.images equals images. If false, this check fails with AssertionError.
    assert model.images == images
    # Assert that any((entry.kind == 'denied' for entry in model.seen[1])). If false, this check
    # fails with AssertionError.
    assert any(entry.kind == "denied" for entry in model.seen[1])
    # Assert that any(('scroll completed' in entry.text for entry in model.seen[2])). If false, this
    # check fails with AssertionError.
    assert any("scroll completed" in entry.text for entry in model.seen[2])


# Define test_bad_code_format_is_denied_and_model_can_retry_without_oracle with no parameters.
def test_bad_code_format_is_denied_and_model_can_retry_without_oracle():
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_agent_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    # Set validate to runpy.run_path(str(script))['validate_code_answer'].
    validate = runpy.run_path(str(script))["validate_code_answer"]
    # Set model to VisionScript([ToolCall('finish', {'answer': 'visual=51,174'}), ToolCall('finish',
    # {'answer': 'ABC123'})]).
    model = VisionScript([ToolCall("finish", {"answer": "visual=51,174"}),
                          # Call ToolCall with the arguments shown.
                          ToolCall("finish", {"answer": "ABC123"})])
    # Set screenshots to an empty list.
    screenshots = []
    # Set desktop to Mock().
    desktop = Mock()
    # Set result to run_vision_agent('Read the target code', GRANT, desktop, model,
    # finish_validator=validate, on_screenshot=lambda step, image: screenshots.append((step,
    # image))).
    result = run_vision_agent("Read the target code", GRANT, desktop, model,
                              # Set finish_validator to (validate,).
                              finish_validator=validate,
                              on_screenshot=lambda step, image: screenshots.append((step, image)))
    # Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Assert that result.answer equals 'ABC123'. If false, this check fails with AssertionError.
    assert result.answer == "ABC123"
    # Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Assert that 'six hexadecimal' is in result.denied[0][1].reason. If false, this check fails
    # with AssertionError.
    assert "six hexadecimal" in result.denied[0][1].reason
    # Assert that 'ABC123' is not in result.denied[0][1].reason. If false, this check fails with
    # AssertionError.
    assert "ABC123" not in result.denied[0][1].reason
    # Assert that a list built from screenshots by the comprehension equals a new list containing 1,
    # 2. If false, this check fails with AssertionError.
    assert [step for step, image in screenshots] == [1, 2]
    # Assert that a list built from screenshots by the comprehension equals model.images. If false,
    # this check fails with AssertionError.
    assert [image for step, image in screenshots] == model.images
    # Assert that any((entry.kind == 'denied' for entry in model.seen[1])). If false, this check
    # fails with AssertionError.
    assert any(entry.kind == "denied" for entry in model.seen[1])


# Define test_vision_loop_stops_repeated_scrolls_at_step_limit with no parameters.
def test_vision_loop_stops_repeated_scrolls_at_step_limit():
    # Set desktop to Mock().
    desktop = Mock()
    # Set model to VisionScript([ToolCall('scroll', {'direction': 'down', 'amount': 1})] * 3).
    model = VisionScript([ToolCall("scroll", {"direction": "down", "amount": 1})] * 3)
    # Set result to run_vision_agent('Keep searching', GRANT, desktop, model, max_steps=3).
    result = run_vision_agent("Keep searching", GRANT, desktop, model, max_steps=3)
    # Assert that result.status equals 'step_limit'. If false, this check fails with AssertionError.
    assert result.status == "step_limit"
    # Assert that desktop.scroll.call_count equals 3. If false, this check fails with
    # AssertionError.
    assert desktop.scroll.call_count == 3
    # Assert that desktop.capture_screen.call_count equals 3. If false, this check fails with
    # AssertionError.
    assert desktop.capture_screen.call_count == 3


# Define test_vision_loop_does_not_execute_late_model_proposal with no parameters.
def test_vision_loop_does_not_execute_late_model_proposal():
    # Set now to [0].
    now = [0]
    # Set (desktop, model) to (Mock(), Mock()).
    desktop, model = Mock(), Mock()
    # Define decide with no parameters.
    def decide(*args):
        # Set now[0] to 121.
        now[0] = 121
        # Return ToolCall('scroll', {'direction': 'down', 'amount': 1}).
        return ToolCall("scroll", {"direction": "down", "amount": 1})
    # Set model.decide.side_effect to decide.
    model.decide.side_effect = decide
    # Set result to run_vision_agent('Find code', GRANT, desktop, model, clock=lambda : now[0]).
    result = run_vision_agent("Find code", GRANT, desktop, model, clock=lambda: now[0])
    # Assert that result.status equals 'deadline'. If false, this check fails with AssertionError.
    assert result.status == "deadline"
    # Call desktop.scroll.assert_not_called with no arguments.
    desktop.scroll.assert_not_called()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("call", [ToolCall("click", {"x": 1, "y": 1}),
                                  # Call ToolCall with the arguments shown.
                                  ToolCall("finish", {"answer": " "}),
                                  # Call ToolCall with the arguments shown.
                                  ToolCall("scroll", {"direction": "down", "amount": True})])
# Define test_vision_loop_rejects_unsupported_and_invalid_actions with parameters call.
def test_vision_loop_rejects_unsupported_and_invalid_actions(call):
    # Set desktop to Mock().
    desktop = Mock()
    # Set result to run_vision_agent('Find code', GRANT, desktop, VisionScript([call]),
    # max_steps=1).
    result = run_vision_agent("Find code", GRANT, desktop, VisionScript([call]), max_steps=1)
    # Assert that result.status equals 'step_limit'. If false, this check fails with AssertionError.
    assert result.status == "step_limit"
    # Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Call desktop.scroll.assert_not_called with no arguments.
    desktop.scroll.assert_not_called()


# Define test_vision_scroll_requires_grant_even_when_model_proposes_it with no parameters.
def test_vision_scroll_requires_grant_even_when_model_proposes_it():
    # Set desktop to Mock().
    desktop = Mock()
    # Set grant to TaskGrant('no-scroll', frozenset({'screenshot', 'finish'}), frozenset()).
    grant = TaskGrant("no-scroll", frozenset({"screenshot", "finish"}), frozenset())
    # Set result to run_vision_agent('Find code', grant, desktop, VisionScript([ToolCall('scroll',
    # {'direction': 'down', 'amount': 1})]), max_steps=1).
    result = run_vision_agent("Find code", grant, desktop,
                              # Pass keyword max_steps = 1.
                              VisionScript([ToolCall("scroll", {"direction": "down", "amount": 1})]), max_steps=1)
    # Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Call desktop.scroll.assert_not_called with no arguments.
    desktop.scroll.assert_not_called()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("kwargs", [{"max_steps": 0}, {"max_steps": True}, {"max_steps": 11},
                                    # Call float with the arguments shown.
                                    {"deadline_seconds": 0}, {"deadline_seconds": float("inf")}])
# Define test_vision_limits_are_validated_before_capture with parameters kwargs.
def test_vision_limits_are_validated_before_capture(kwargs):
    # Set desktop to Mock().
    desktop = Mock()
    # Use pytest.raises(ValueError); leave the context and run its cleanup when this block ends.
    with pytest.raises(ValueError):
        # Call run_vision_agent with 'Find code', GRANT, desktop, Mock().
        run_vision_agent("Find code", GRANT, desktop, Mock(), **kwargs)
    # Call desktop.capture_screen.assert_not_called with no arguments.
    desktop.capture_screen.assert_not_called()


# Define response with parameters name, args, reason.
def response(name, args, reason="tool_calls"):
    return NS(choices=[NS(finish_reason=reason, message=NS(tool_calls=[
        # Call NS with no arguments.
        NS(type="function", function=NS(name=name, arguments=json.dumps(args)))
    ]))])


# Define test_vision_proposals_use_one_current_image_and_structured_tools with no parameters.
def test_vision_proposals_use_one_current_image_and_structured_tools():
    # Import base64: encodes PNG bytes as text for a model image data URL.
    import base64
    # Set png to
    # base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=').
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=")
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.return_value to response('scroll', {'direction': 'down',
    # 'amount': 2}).
    client.chat.completions.create.return_value = response("scroll", {"direction": "down", "amount": 2})
    # Set proposal to GroqVision(client=client).decide(Screenshot(png), [Entry('goal', 'Find code
    # below')]).
    proposal = GroqVision(client=client).decide(Screenshot(png), [Entry("goal", "Find code below")])
    # Assert that proposal.call equals ToolCall('scroll', {'direction': 'down', 'amount': 2}). If
    # false, this check fails with AssertionError.
    assert proposal.call == ToolCall("scroll", {"direction": "down", "amount": 2})
    # Set request to client.chat.completions.create.call_args.kwargs.
    request = client.chat.completions.create.call_args.kwargs
    # Assert that request['tool_choice'] equals 'required'. If false, this check fails with
    # AssertionError.
    assert request["tool_choice"] == "required"
    # Assert that request['parallel_tool_calls'] is False. If false, this check fails with
    # AssertionError.
    assert request["parallel_tool_calls"] is False
    # Assert that {tool['function']['name'] for tool in request['tools']} equals a set of 'scroll',
    # 'finish' (unique members). If false, this check fails with AssertionError.
    assert {tool["function"]["name"] for tool in request["tools"]} == {"scroll", "finish"}
    # Set content to request['messages'][1]['content'].
    content = request["messages"][1]["content"]
    # Assert that a list built from content by the comprehension equals a new list containing
    # 'text', 'image_url'. If false, this check fails with AssertionError.
    assert [block["type"] for block in content] == ["text", "image_url"]
    # Assert that base64.b64decode(content[1]['image_url']['url'].split(',')[1]) equals png. If
    # false, this check fails with AssertionError.
    assert base64.b64decode(content[1]["image_url"]["url"].split(",")[1]) == png


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("bad", [response("click", {}), response("finish", {"answer": ""}),
                                  # Call response with the arguments shown.
                                  response("scroll", {"amount": 3}), response("finish", [], "length"),
                                  # Pass keyword choices = a new list (empty).
                                  NS(choices=[])])
# Define test_malformed_vision_proposals_fail_without_action with parameters bad.
def test_malformed_vision_proposals_fail_without_action(bad):
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.return_value to bad.
    client.chat.completions.create.return_value = bad
    # Use pytest.raises(ValueError); leave the context and run its cleanup when this block ends.
    with pytest.raises(ValueError):
        # Call GroqVision(client=client).decide with NS(png=b'fixture'), an empty list.
        GroqVision(client=client).decide(NS(png=b"fixture"), [])


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("failure", [False, True])
# Define test_agent_demo_cleans_up_and_does_not_put_expected_code_in_goal with parameters
# monkeypatch, failure, capsys.
def test_agent_demo_cleans_up_and_does_not_put_expected_code_in_goal(monkeypatch, failure, capsys):
    # Call monkeypatch.setenv with 'E2B_API_KEY', 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Call monkeypatch.setenv with 'GROQ_API_KEY', 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Call monkeypatch.setattr with sys, 'argv', ['e2b_vision_agent_demo.py'].
    monkeypatch.setattr(sys, "argv", ["e2b_vision_agent_demo.py"])
    # Set codes to iter(['abc123', 'def456']).
    codes = iter(["abc123", "def456"])
    # Call monkeypatch.setattr with 'secrets.token_hex', a function that returns next(codes) when
    # called.
    monkeypatch.setattr("secrets.token_hex", lambda n: next(codes))
    # Set closed to an empty list.
    closed = []
    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define open_desktop with parameters grant.
    def open_desktop(grant):
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give Mock() to the caller and pause here until execution resumes.
            yield Mock()
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Append True to closed.
            closed.append(True)
    # Define run with parameters goal, grant, desktop, model.
    def run(goal, grant, desktop, model, **kwargs):
        # Assert that 'ABC123' is not in goal AND 'DEF456' is not in goal. If false, this check
        # fails with AssertionError.
        assert "ABC123" not in goal and "DEF456" not in goal
        # Check whether failure.
        if failure:
            # Raise RuntimeError('Vision failed') to stop the normal path.
            raise RuntimeError("Vision failed")
        # Return NS(status='finished', answer='DEF456', denied=[], transcript=[]).
        return NS(status="finished", answer="DEF456", denied=[], transcript=[])
    # Call monkeypatch.setattr with 'crescendo_agent.e2b_desktop.open_e2b_desktop', open_desktop.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    # Call monkeypatch.setattr with 'crescendo_agent.vision.GroqVision', a function that returns
    # NS(model=name) when called.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: NS(model=name))
    # Call monkeypatch.setattr with 'crescendo_agent.vision_loop.run_vision_agent', run.
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_agent_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    # Check whether failure.
    if failure:
        # Use pytest.raises(RuntimeError, match='Vision failed'); leave the context and run its
        # cleanup when this block ends.
        with pytest.raises(RuntimeError, match="Vision failed"):
            # Call runpy.run_path with script converted to a string.
            runpy.run_path(str(script), run_name="__main__")
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Call runpy.run_path with script converted to a string.
        runpy.run_path(str(script), run_name="__main__")
        # Assert that 'PASS' is in capsys.readouterr().out. If false, this check fails with
        # AssertionError.
        assert "PASS" in capsys.readouterr().out
    # Assert that closed equals a new list containing True. If false, this check fails with
    # AssertionError.
    assert closed == [True]
