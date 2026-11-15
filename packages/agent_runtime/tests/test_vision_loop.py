# Learn: From contextlib, import contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
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
# Learn: From crescendo_agent.vision, import GroqVision (adapts screenshot observations to Groq vision
# requests); Screenshot (validates the PNG container and dimensions at the image boundary).
from crescendo_agent.vision import GroqVision, Screenshot
# Learn: From crescendo_agent.vision_loop, import run_vision_agent (runs the bounded
# screenshot/proposal/authorization/action loop).
from crescendo_agent.vision_loop import run_vision_agent
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall

# Learn: Set GRANT to TaskGrant('vision', frozenset({'screenshot', 'scroll', 'finish'}), frozenset()).
GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())


# Learn: Define VisionScript. Indented methods and attributes belong to this class.
class VisionScript:
    # Learn: Define __init__(calls). This initializes or validates each new instance.
    def __init__(self, calls):
        # Learn: Set self.calls to iter(calls); the model tool-call proposals or scripted calls.
        self.calls = iter(calls)
        # Learn: Set self.seen to a new list (empty); the values already encountered, used to avoid
        # duplicates.
        self.seen = []
        # Learn: Set self.images to a new list (empty).
        self.images = []

    # Learn: Define decide(image, transcript). The body runs when called, not when defined.
    def decide(self, image, transcript):
        # Learn: Append one item to the ordered collection on self.images; inputs: image.
        self.images.append(image)
        # Learn: Append one item to the ordered collection on self.seen; inputs: list(transcript).
        self.seen.append(list(transcript))
        # Learn: Return next(self.calls) to the caller and stop this function.
        return next(self.calls)


# Learn: Test vision loop denies invalid scroll then acts and observes again. pytest supplies named fixtures
# and checks assertions below.
def test_vision_loop_denies_invalid_scroll_then_acts_and_observes_again():
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set images to a list built from range(3) by the comprehension.
    images = [Mock(size=(1024, 768)) for _ in range(3)]
    # Learn: Set desktop.capture_screen.side_effect to images.
    desktop.capture_screen.side_effect = images
    # Learn: Set model to VisionScript([ToolCall('scroll', {'direction': 'down', 'amount': 100}),
    # ToolCall('scroll', {'direction': 'down', 'amount': 3}), Tool...; the provider adapter or scripted test
    # model used to propose actions.
    model = VisionScript([
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("scroll", {"direction": "down", "amount": 100}),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("scroll", {"direction": "down", "amount": 3}),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "Visual code ABC123"}),
    # Learn: Close this list literal; delimiters group the values into one object.
    ])
    # Learn: Set result to run_vision_agent('Read code below', GRANT, desktop, model); the operation outcome
    # for subsequent checks or reporting.
    result = run_vision_agent("Read code below", GRANT, desktop, model)
    # Learn: Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Learn: Assert that result.answer equals 'Visual code ABC123'. If false, this check fails with
    # AssertionError.
    assert result.answer == "Visual code ABC123"
    # Learn: Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Learn: Verify the fake dependency ran exactly once with these arguments on desktop.scroll; inputs:
    # 'down', 3.
    desktop.scroll.assert_called_once_with("down", 3)
    # Learn: Assert that model.images equals images. If false, this check fails with AssertionError.
    assert model.images == images
    # Learn: Assert that any((entry.kind == 'denied' for entry in model.seen[1])). If false, this check
    # fails with AssertionError.
    assert any(entry.kind == "denied" for entry in model.seen[1])
    # Learn: Assert that any(('scroll completed' in entry.text for entry in model.seen[2])). If false, this
    # check fails with AssertionError.
    assert any("scroll completed" in entry.text for entry in model.seen[2])


# Learn: Test bad code format is denied and model can retry without oracle. pytest supplies named fixtures
# and checks assertions below.
def test_bad_code_format_is_denied_and_model_can_retry_without_oracle():
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_agent_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    # Learn: Set validate to runpy.run_path(str(script))['validate_code_answer'].
    validate = runpy.run_path(str(script))["validate_code_answer"]
    # Learn: Set model to VisionScript([ToolCall('finish', {'answer': 'visual=51,174'}), ToolCall('finish',
    # {'answer': 'ABC123'})]); the provider adapter or scripted test model used to propose actions.
    model = VisionScript([ToolCall("finish", {"answer": "visual=51,174"}),
                          # Learn: Call ToolCall with the arguments shown.
                          ToolCall("finish", {"answer": "ABC123"})])
    # Learn: Set screenshots to a new list (empty).
    screenshots = []
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set result to run_vision_agent('Read the target code', GRANT, desktop, model,
    # finish_validator=validate, on_screenshot=lambda step, image: screens...; the operation outcome for
    # subsequent checks or reporting.
    result = run_vision_agent("Read the target code", GRANT, desktop, model,
                              # Learn: Pass keyword finish_validator = validate.
                              finish_validator=validate,
                              # Learn: Parameters: step is provided/defaulted by the caller; image is
                              # provided/defaulted by the caller. Type hints do not enforce types by
                              # themselves.
                              on_screenshot=lambda step, image: screenshots.append((step, image)))
    # Learn: Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Learn: Assert that result.answer equals 'ABC123'. If false, this check fails with AssertionError.
    assert result.answer == "ABC123"
    # Learn: Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Learn: Assert that 'six hexadecimal' is in result.denied[0][1].reason. If false, this check fails with
    # AssertionError.
    assert "six hexadecimal" in result.denied[0][1].reason
    # Learn: Assert that 'ABC123' is not in result.denied[0][1].reason. If false, this check fails with
    # AssertionError.
    assert "ABC123" not in result.denied[0][1].reason
    # Learn: Assert that a list built from screenshots by the comprehension equals a new list containing 1,
    # 2. If false, this check fails with AssertionError.
    assert [step for step, image in screenshots] == [1, 2]
    # Learn: Assert that a list built from screenshots by the comprehension equals model.images. If false,
    # this check fails with AssertionError.
    assert [image for step, image in screenshots] == model.images
    # Learn: Assert that any((entry.kind == 'denied' for entry in model.seen[1])). If false, this check
    # fails with AssertionError.
    assert any(entry.kind == "denied" for entry in model.seen[1])


# Learn: Test vision loop stops repeated scrolls at step limit. pytest supplies named fixtures and checks
# assertions below.
def test_vision_loop_stops_repeated_scrolls_at_step_limit():
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set model to VisionScript([ToolCall('scroll', {'direction': 'down', 'amount': 1})] * 3); the
    # provider adapter or scripted test model used to propose actions.
    model = VisionScript([ToolCall("scroll", {"direction": "down", "amount": 1})] * 3)
    # Learn: Set result to run_vision_agent('Keep searching', GRANT, desktop, model, max_steps=3); the
    # operation outcome for subsequent checks or reporting.
    result = run_vision_agent("Keep searching", GRANT, desktop, model, max_steps=3)
    # Learn: Assert that result.status equals 'step_limit'. If false, this check fails with AssertionError.
    assert result.status == "step_limit"
    # Learn: Assert that desktop.scroll.call_count equals 3. If false, this check fails with AssertionError.
    assert desktop.scroll.call_count == 3
    # Learn: Assert that desktop.capture_screen.call_count equals 3. If false, this check fails with
    # AssertionError.
    assert desktop.capture_screen.call_count == 3


# Learn: Test vision loop does not execute late model proposal. pytest supplies named fixtures and checks
# assertions below.
def test_vision_loop_does_not_execute_late_model_proposal():
    # Learn: Set now to a new list containing 0.
    now = [0]
    # Learn: Set (desktop, model) to the tuple (Mock(), Mock()) (positional values).
    desktop, model = Mock(), Mock()
    # Learn: Define decide(). The body runs when called, not when defined.
    def decide(*args):
        # Learn: Set now[0] to 121.
        now[0] = 121
        # Learn: Return ToolCall('scroll', {'direction': 'down', 'amount': 1}) to the caller and stop this
        # function.
        return ToolCall("scroll", {"direction": "down", "amount": 1})
    # Learn: Set model.decide.side_effect to decide.
    model.decide.side_effect = decide
    # Learn: Set result to run_vision_agent('Find code', GRANT, desktop, model, clock=lambda : now[0]); the
    # operation outcome for subsequent checks or reporting.
    result = run_vision_agent("Find code", GRANT, desktop, model, clock=lambda: now[0])
    # Learn: Assert that result.status equals 'deadline'. If false, this check fails with AssertionError.
    assert result.status == "deadline"
    # Learn: Verify the denied/error path never invoked this fake dependency on desktop.scroll.
    desktop.scroll.assert_not_called()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("call", [ToolCall("click", {"x": 1, "y": 1}),
                                  # Learn: Call ToolCall with the arguments shown.
                                  ToolCall("finish", {"answer": " "}),
                                  # Learn: Call ToolCall with the arguments shown.
                                  ToolCall("scroll", {"direction": "down", "amount": True})])
# Learn: Test vision loop rejects unsupported and invalid actions. pytest supplies named fixtures and checks
# assertions below.
def test_vision_loop_rejects_unsupported_and_invalid_actions(call):
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set result to run_vision_agent('Find code', GRANT, desktop, VisionScript([call]), max_steps=1);
    # the operation outcome for subsequent checks or reporting.
    result = run_vision_agent("Find code", GRANT, desktop, VisionScript([call]), max_steps=1)
    # Learn: Assert that result.status equals 'step_limit'. If false, this check fails with AssertionError.
    assert result.status == "step_limit"
    # Learn: Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Learn: Verify the denied/error path never invoked this fake dependency on desktop.scroll.
    desktop.scroll.assert_not_called()


# Learn: Test vision scroll requires grant even when model proposes it. pytest supplies named fixtures and
# checks assertions below.
def test_vision_scroll_requires_grant_even_when_model_proposes_it():
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set grant to TaskGrant('no-scroll', frozenset({'screenshot', 'finish'}), frozenset()); the task
    # identity and fixed tool/host permissions; model output cannot expand these.
    grant = TaskGrant("no-scroll", frozenset({"screenshot", "finish"}), frozenset())
    # Learn: Set result to run_vision_agent('Find code', grant, desktop, VisionScript([ToolCall('scroll',
    # {'direction': 'down', 'amount': 1})]), max_steps=1); the operation outcome for subsequent checks or
    # reporting.
    result = run_vision_agent("Find code", grant, desktop,
                              # Learn: Pass keyword max_steps = 1.
                              VisionScript([ToolCall("scroll", {"direction": "down", "amount": 1})]), max_steps=1)
    # Learn: Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Learn: Verify the denied/error path never invoked this fake dependency on desktop.scroll.
    desktop.scroll.assert_not_called()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("kwargs", [{"max_steps": 0}, {"max_steps": True}, {"max_steps": 11},
                                    # Learn: Call float with the arguments shown.
                                    {"deadline_seconds": 0}, {"deadline_seconds": float("inf")}])
# Learn: Test vision limits are validated before capture. pytest supplies named fixtures and checks
# assertions below.
def test_vision_limits_are_validated_before_capture(kwargs):
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Enter pytest.raises(ValueError). The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with pytest.raises(ValueError):
        # Learn: Call run_vision_agent with the arguments shown.
        run_vision_agent("Find code", GRANT, desktop, Mock(), **kwargs)
    # Learn: Verify the denied/error path never invoked this fake dependency on desktop.capture_screen.
    desktop.capture_screen.assert_not_called()


# Learn: Define response(name, args, reason). The body runs when called, not when defined.
def response(name, args, reason="tool_calls"):
    # Learn: Return NS(choices=[NS(finish_reason=reason, message=NS(tool_calls=[NS(type='function',
    # function=NS(name=name, arguments=json.dumps(args)))]... to the caller and stop this function.
    return NS(choices=[NS(finish_reason=reason, message=NS(tool_calls=[
        # Learn: Pass keyword type = 'function'.
        NS(type="function", function=NS(name=name, arguments=json.dumps(args)))
    # Learn: Close this list literal; delimiters group the values into one object.
    ]))])


# Learn: Test vision proposals use one current image and structured tools. pytest supplies named fixtures
# and checks assertions below.
def test_vision_proposals_use_one_current_image_and_structured_tools():
    # Learn: Import base64: encodes PNG bytes as text for a model image data URL.
    import base64
    # Learn: Set png to
    # base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=');
    # the image bytes; repr suppression keeps large image data out of ordinary logs.
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=")
    # Learn: Set client to Mock(); the HTTP/model client, often injectable so tests avoid live calls.
    client = Mock()
    # Learn: Set client.chat.completions.create.return_value to response('scroll', {'direction': 'down',
    # 'amount': 2}).
    client.chat.completions.create.return_value = response("scroll", {"direction": "down", "amount": 2})
    # Learn: Set proposal to GroqVision(client=client).decide(Screenshot(png), [Entry('goal', 'Find code
    # below')]); the model action plus its optional, untrusted display reason. Ask the adapter for a
    # proposal; this does not itself execute a tool.
    proposal = GroqVision(client=client).decide(Screenshot(png), [Entry("goal", "Find code below")])
    # Learn: Assert that proposal.call equals ToolCall('scroll', {'direction': 'down', 'amount': 2}). If
    # false, this check fails with AssertionError.
    assert proposal.call == ToolCall("scroll", {"direction": "down", "amount": 2})
    # Learn: Set request to client.chat.completions.create.call_args.kwargs.
    request = client.chat.completions.create.call_args.kwargs
    # Learn: Assert that request['tool_choice'] equals 'required'. If false, this check fails with
    # AssertionError.
    assert request["tool_choice"] == "required"
    # Learn: Assert that request['parallel_tool_calls'] is False. If false, this check fails with
    # AssertionError.
    assert request["parallel_tool_calls"] is False
    # Learn: Assert that {tool['function']['name'] for tool in request['tools']} equals a set of 'scroll',
    # 'finish' (unique members). If false, this check fails with AssertionError.
    assert {tool["function"]["name"] for tool in request["tools"]} == {"scroll", "finish"}
    # Learn: Set content to request['messages'][1]['content']; the selected page region or content to write.
    content = request["messages"][1]["content"]
    # Learn: Assert that a list built from content by the comprehension equals a new list containing 'text',
    # 'image_url'. If false, this check fails with AssertionError.
    assert [block["type"] for block in content] == ["text", "image_url"]
    # Learn: Assert that base64.b64decode(content[1]['image_url']['url'].split(',')[1]) equals png. If
    # false, this check fails with AssertionError.
    assert base64.b64decode(content[1]["image_url"]["url"].split(",")[1]) == png


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("bad", [response("click", {}), response("finish", {"answer": ""}),
                                  # Learn: Call response with the arguments shown.
                                  response("scroll", {"amount": 3}), response("finish", [], "length"),
                                  # Learn: Pass keyword choices = a new list (empty).
                                  NS(choices=[])])
# Learn: Test malformed vision proposals fail without action. pytest supplies named fixtures and checks
# assertions below.
def test_malformed_vision_proposals_fail_without_action(bad):
    # Learn: Set client to Mock(); the HTTP/model client, often injectable so tests avoid live calls.
    client = Mock()
    # Learn: Set client.chat.completions.create.return_value to bad.
    client.chat.completions.create.return_value = bad
    # Learn: Enter pytest.raises(ValueError). The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with pytest.raises(ValueError):
        # Learn: Ask the adapter for a proposal; this does not itself execute a tool on
        # GroqVision(client=client); inputs: NS(png=b'fixture'), a new list (empty).
        GroqVision(client=client).decide(NS(png=b"fixture"), [])


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("failure", [False, True])
# Learn: Test agent demo cleans up and does not put expected code in goal. pytest supplies named fixtures
# and checks assertions below.
def test_agent_demo_cleans_up_and_does_not_put_expected_code_in_goal(monkeypatch, failure, capsys):
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'E2B_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-key")
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'GROQ_API_KEY',
    # 'offline-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-key")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr(sys, "argv", ["e2b_vision_agent_demo.py"])
    # Learn: Set codes to iter(['abc123', 'def456']).
    codes = iter(["abc123", "def456"])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("secrets.token_hex", lambda n: next(codes))
    # Learn: Set closed to a new list (empty).
    closed = []
    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Learn: Define open_desktop(grant). The body runs when called, not when defined.
    def open_desktop(grant):
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Yield Mock() to the with-block/request; resume here for cleanup afterward.
            yield Mock()
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Append one item to the ordered collection on closed; inputs: True.
            closed.append(True)
    # Learn: Define run(goal, grant, desktop, model). The body runs when called, not when defined.
    def run(goal, grant, desktop, model, **kwargs):
        # Learn: Assert that 'ABC123' is not in goal AND 'DEF456' is not in goal. If false, this check fails
        # with AssertionError.
        assert "ABC123" not in goal and "DEF456" not in goal
        # Learn: Take this branch only if failure.
        if failure:
            # Learn: Raise RuntimeError('Vision failed') to stop the normal path.
            raise RuntimeError("Vision failed")
        # Learn: Return NS(status='finished', answer='DEF456', denied=[], transcript=[]) to the caller and
        # stop this function.
        return NS(status="finished", answer="DEF456", denied=[], transcript=[])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", open_desktop)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: NS(model=name))
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision_loop.run_vision_agent", run)
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_agent_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_agent_demo.py"
    # Learn: Take this branch only if failure.
    if failure:
        # Learn: Enter pytest.raises(RuntimeError, match='Vision failed'). The context manager controls
        # setup/exit; inspect it for the actual cleanup behavior.
        with pytest.raises(RuntimeError, match="Vision failed"):
            # Learn: Call runpy.run_path with the arguments shown.
            runpy.run_path(str(script), run_name="__main__")
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(script), run_name="__main__")
        # Learn: Assert that 'PASS' is in capsys.readouterr().out. If false, this check fails with
        # AssertionError.
        assert "PASS" in capsys.readouterr().out
    # Learn: Assert that closed equals a new list containing True. If false, this check fails with
    # AssertionError.
    assert closed == [True]
