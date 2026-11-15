# Learn: Import base64: encodes PNG bytes as text for a model image data URL.
import base64
# Learn: From contextlib, import contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Learn: From pathlib, import Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Learn: Import runpy: use this module through its namespace.
import runpy
# Learn: Import struct: reads binary PNG dimension fields with an explicit byte order.
import struct
# Learn: Import sys: provides process details and standard input/output streams.
import sys
# Learn: From types, import SimpleNamespace (builds a small object with named attributes for test fixtures).
from types import SimpleNamespace
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.e2b_desktop, import E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Learn: From crescendo_agent.vision, import GroqVision (adapts screenshot observations to Groq vision
# requests); Screenshot (validates the PNG container and dimensions at the image boundary).
from crescendo_agent.vision import GroqVision, Screenshot
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant

# Learn: Set PNG to
# base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=').
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=")


# Learn: Test vision sends real image block instead of stringifying bytes. pytest supplies named fixtures
# and checks assertions below.
def test_vision_sends_real_image_block_instead_of_stringifying_bytes():
    # Learn: Set client to Mock(); the HTTP/model client, often injectable so tests avoid live calls.
    client = Mock()
    # Learn: Set client.chat.completions.create.return_value to
    # SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content='Visual
    # code: ABC123'))]).
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        # Learn: Pass keyword finish_reason = 'stop'.
        finish_reason="stop", message=SimpleNamespace(content="Visual code: ABC123"))])
    # Learn: Set screenshot to Screenshot(PNG); the current PNG observation supplied to the vision model.
    screenshot = Screenshot(PNG)
    # Learn: Assert that GroqVision(client=client).describe(screenshot) equals 'Visual code: ABC123'. If
    # false, this check fails with AssertionError.
    assert GroqVision(client=client).describe(screenshot) == "Visual code: ABC123"
    # Learn: Set request to client.chat.completions.create.call_args.kwargs.
    request = client.chat.completions.create.call_args.kwargs
    # Learn: Set content to request['messages'][1]['content']; the selected page region or content to write.
    content = request["messages"][1]["content"]
    # Learn: Assert that content[0]['type'] equals 'text'. If false, this check fails with AssertionError.
    assert content[0]["type"] == "text"
    # Learn: Assert that 'ABC123' is not in content[0]['text']. If false, this check fails with
    # AssertionError.
    assert "ABC123" not in content[0]["text"]
    # Learn: Assert that content[1]['type'] equals 'image_url'. If false, this check fails with
    # AssertionError.
    assert content[1]["type"] == "image_url"
    # Learn: Set (prefix, data) to content[1]['image_url']['url'].split(',', 1).
    prefix, data = content[1]["image_url"]["url"].split(",", 1)
    # Learn: Assert that prefix equals 'data:image/png;base64'. If false, this check fails with
    # AssertionError.
    assert prefix == "data:image/png;base64"
    # Learn: Assert that base64.b64decode(data) equals PNG. If false, this check fails with AssertionError.
    assert base64.b64decode(data) == PNG
    # Learn: Assert that request['max_completion_tokens'] equals 512. If false, this check fails with
    # AssertionError.
    assert request["max_completion_tokens"] == 512
    # Learn: Assert that request['reasoning_effort'] equals 'none'. If false, this check fails with
    # AssertionError.
    assert request["reasoning_effort"] == "none"
    # Learn: Assert that 'tools' is not in request. If false, this check fails with AssertionError.
    assert "tools" not in request
    # Learn: Assert that screenshot.size equals the tuple (1, 1) (positional values). If false, this check
    # fails with AssertionError.
    assert screenshot.size == (1, 1)
    # Learn: Assert that repr(screenshot) equals 'Screenshot()'. If false, this check fails with
    # AssertionError.
    assert repr(screenshot) == "Screenshot()"


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("data", [b"", b"not a png" * 10, PNG * 100000,
                                   # Learn: Call struct.pack with the arguments shown.
                                   PNG[:16] + struct.pack(">II", 0, 10),
                                   # Learn: Call struct.pack with the arguments shown.
                                   PNG[:16] + struct.pack(">II", 9000, 10)])
# Learn: Test invalid or oversized screenshot is rejected. pytest supplies named fixtures and checks
# assertions below.
def test_invalid_or_oversized_screenshot_is_rejected(data):
    # Learn: Enter pytest.raises(ValueError). The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with pytest.raises(ValueError):
        # Learn: Call Screenshot with the arguments shown.
        Screenshot(data)


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("reason,text", [("length", "partial"), ("stop", ""), ("stop", None)])
# Learn: Test incomplete or empty vision response is rejected. pytest supplies named fixtures and checks
# assertions below.
def test_incomplete_or_empty_vision_response_is_rejected(reason, text):
    # Learn: Set client to Mock(); the HTTP/model client, often injectable so tests avoid live calls.
    client = Mock()
    # Learn: Set client.chat.completions.create.return_value to
    # SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason,
    # message=SimpleNamespace(content=text))]).
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        # Learn: Pass keyword finish_reason = reason.
        finish_reason=reason, message=SimpleNamespace(content=text))])
    # Learn: Enter pytest.raises(ValueError, match='complete'). The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with pytest.raises(ValueError, match="complete"):
        # Learn: Call GroqVision(client=client).describe with the arguments shown.
        GroqVision(client=client).describe(Screenshot(PNG))


# Learn: Test capture requires grant before touching desktop. pytest supplies named fixtures and checks
# assertions below.
def test_capture_requires_grant_before_touching_desktop():
    # Learn: Set (page, provider) to the tuple (Mock(), Mock(return_value=PNG)) (positional values).
    page, provider = Mock(), Mock(return_value=PNG)
    # Learn: Set desktop to E2BDesktop(page, Mock(), TaskGrant('no-capture', frozenset(), frozenset()),
    # screenshot_provider=provider).
    desktop = E2BDesktop(page, Mock(), TaskGrant("no-capture", frozenset(), frozenset()),
                         # Learn: Pass keyword screenshot_provider = provider.
                         screenshot_provider=provider)
    # Learn: Enter pytest.raises(ValueError, match='not permitted'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(ValueError, match="not permitted"):
        # Learn: Capture a fresh whole-desktop PNG through the permission-checked adapter on desktop.
        desktop.capture_screen()
    # Learn: Verify the denied/error path never invoked this fake dependency on provider.
    provider.assert_not_called()
    # Learn: Verify the denied/error path never invoked this fake dependency on page.bring_to_front.
    page.bring_to_front.assert_not_called()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("provider_type", [bytes, bytearray])
# Learn: Test capture foregrounds page before calling provider. pytest supplies named fixtures and checks
# assertions below.
def test_capture_foregrounds_page_before_calling_provider(provider_type):
    # Learn: Set page to Mock(); the browser tab controlled by Playwright.
    page = Mock()
    # Learn: Set payload to provider_type(PNG).
    payload = provider_type(PNG)
    # Learn: Define provider(). The body runs when called, not when defined.
    def provider():
        # Learn: Verify the fake dependency ran exactly once with these arguments on page.bring_to_front.
        page.bring_to_front.assert_called_once_with()
        # Learn: Return payload to the caller and stop this function.
        return payload
    # Learn: Set desktop to E2BDesktop(page, Mock(), TaskGrant('capture', frozenset({'screenshot'}),
    # frozenset()), screenshot_provider=provider).
    desktop = E2BDesktop(page, Mock(), TaskGrant("capture", frozenset({"screenshot"}), frozenset()),
                         # Learn: Pass keyword screenshot_provider = provider.
                         screenshot_provider=provider)
    # Learn: Set screenshot to desktop.capture_screen(); the current PNG observation supplied to the vision
    # model. Capture a fresh whole-desktop PNG through the permission-checked adapter.
    screenshot = desktop.capture_screen()
    # Learn: Assert that screenshot.png equals PNG. If false, this check fails with AssertionError.
    assert screenshot.png == PNG
    # Learn: Assert that screenshot.png has type bytes (including subclasses). If false, this check fails
    # with AssertionError.
    assert isinstance(screenshot.png, bytes)
    # Learn: Take this branch only if payload has type bytearray (including subclasses).
    if isinstance(payload, bytearray):
        # Learn: Set payload[0] to 0.
        payload[0] = 0
        # Learn: Assert that screenshot.png equals PNG. If false, this check fails with AssertionError.
        assert screenshot.png == PNG


# Learn: Test invalid bytearray still fails screenshot validation. pytest supplies named fixtures and checks
# assertions below.
def test_invalid_bytearray_still_fails_screenshot_validation():
    # Learn: Set desktop to E2BDesktop(Mock(), Mock(), TaskGrant('capture', frozenset({'screenshot'}),
    # frozenset()), screenshot_provider=lambda : bytearray(b'no....
    desktop = E2BDesktop(Mock(), Mock(), TaskGrant("capture", frozenset({"screenshot"}), frozenset()),
                         # Learn: Pass keyword screenshot_provider = lambda : bytearray(b'not a PNG').
                         screenshot_provider=lambda: bytearray(b"not a PNG"))
    # Learn: Enter pytest.raises(ValueError, match='PNG'). The context manager controls setup/exit; inspect
    # it for the actual cleanup behavior.
    with pytest.raises(ValueError, match="PNG"):
        # Learn: Capture a fresh whole-desktop PNG through the permission-checked adapter on desktop.
        desktop.capture_screen()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("model_fails", [False, True])
# Learn: Test vision demo cleans up before output and on model failure. pytest supplies named fixtures and
# checks assertions below.
def test_vision_demo_cleans_up_before_output_and_on_model_failure(monkeypatch, capsys, model_fails):
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'E2B_API_KEY',
    # 'offline-e2b-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-e2b-key")
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'GROQ_API_KEY',
    # 'offline-groq-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-key")
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr(sys, "argv", ["e2b_vision_demo.py"])
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("secrets.token_hex", lambda n: "abc123")
    # Learn: Set closed to a new list (empty).
    closed = []
    # Learn: Set desktop to Mock().
    desktop = Mock()
    # Learn: Set desktop.capture_screen.return_value to Screenshot(PNG).
    desktop.capture_screen.return_value = Screenshot(PNG)

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Learn: Define fake_open(grant). The body runs when called, not when defined.
    def fake_open(grant):
        # Learn: Assert that grant.allowed_hosts equals frozenset(). If false, this check fails with
        # AssertionError.
        assert grant.allowed_hosts == frozenset()
        # Learn: Assert that grant.allowed_tools equals frozenset({'screenshot'}). If false, this check
        # fails with AssertionError.
        assert grant.allowed_tools == frozenset({"screenshot"})
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Yield desktop to the with-block/request; resume here for cleanup afterward.
            yield desktop
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Append one item to the ordered collection on closed; inputs: True.
            closed.append(True)

    # Learn: Set model to Mock(); the provider adapter or scripted test model used to propose actions.
    model = Mock()
    # Learn: Set model.model to 'test-vision-model'; the provider adapter or scripted test model used to
    # propose actions.
    model.model = "test-vision-model"
    # Learn: Set model.describe.side_effect to RuntimeError('Model unavailable') when model_fails, otherwise
    # None (no value).
    model.describe.side_effect = RuntimeError("Model unavailable") if model_fails else None
    # Learn: Set model.describe.return_value to 'Visual code: ABC123. The desktop shows Ready.'.
    model.describe.return_value = "Visual code: ABC123. The desktop shows Ready."
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: model)
    # Learn: Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_demo.py"
    # Learn: Take this branch only if model_fails.
    if model_fails:
        # Learn: Enter pytest.raises(RuntimeError, match='Model unavailable'). The context manager controls
        # setup/exit; inspect it for the actual cleanup behavior.
        with pytest.raises(RuntimeError, match="Model unavailable"):
            # Learn: Call runpy.run_path with the arguments shown.
            runpy.run_path(str(script), run_name="__main__")
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Call runpy.run_path with the arguments shown.
        runpy.run_path(str(script), run_name="__main__")
    # Learn: Assert that closed equals a new list containing True. If false, this check fails with
    # AssertionError.
    assert closed == [True]
    # Learn: Verify the fake dependency ran exactly once with these arguments on model.describe; inputs:
    # Screenshot(PNG).
    model.describe.assert_called_once_with(Screenshot(PNG))
    # Learn: Set output to capsys.readouterr().out; the destination stream for the generated bytes or text.
    output = capsys.readouterr().out
    # Learn: Assert that 'offline-e2b-key' is not in output AND 'offline-groq-key' is not in output. If
    # false, this check fails with AssertionError.
    assert "offline-e2b-key" not in output and "offline-groq-key" not in output
    # Learn: Assert that 'data:image' is not in output. If false, this check fails with AssertionError.
    assert "data:image" not in output
    # Learn: Take this branch only if model_fails.
    if model_fails:
        # Learn: Assert that 'PASS' is not in output. If false, this check fails with AssertionError.
        assert "PASS" not in output
    # Learn: Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Learn: Assert that 'PASS: model read the code' is in output. If false, this check fails with
        # AssertionError.
        assert "PASS: model read the code" in output


# Learn: Test vision client does not retry provider error. pytest supplies named fixtures and checks
# assertions below.
def test_vision_client_does_not_retry_provider_error():
    # Learn: Set client to Mock(); the HTTP/model client, often injectable so tests avoid live calls.
    client = Mock()
    # Learn: Set client.chat.completions.create.side_effect to RuntimeError('provider unavailable').
    client.chat.completions.create.side_effect = RuntimeError("provider unavailable")
    # Learn: Enter pytest.raises(RuntimeError, match='provider unavailable'). The context manager controls
    # setup/exit; inspect it for the actual cleanup behavior.
    with pytest.raises(RuntimeError, match="provider unavailable"):
        # Learn: Call GroqVision(client=client).describe with the arguments shown.
        GroqVision(client=client).describe(Screenshot(PNG))
    # Learn: Assert that client.chat.completions.create.call_count equals 1. If false, this check fails with
    # AssertionError.
    assert client.chat.completions.create.call_count == 1


# Learn: Test default vision client has timeout and no sdk retries. pytest supplies named fixtures and
# checks assertions below.
def test_default_vision_client_has_timeout_and_no_sdk_retries(monkeypatch):
    # Learn: Set client_factory to Mock().
    client_factory = Mock()
    # Learn: Call monkeypatch.setattr with the arguments shown.
    monkeypatch.setattr("groq.Groq", client_factory)
    # Learn: Call GroqVision with no arguments.
    GroqVision()
    # Learn: Verify the fake dependency ran exactly once with these arguments on client_factory.
    client_factory.assert_called_once_with(timeout=30.0, max_retries=0)
