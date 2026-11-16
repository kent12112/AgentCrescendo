# Import base64: encodes PNG bytes as text for a model image data URL.
import base64
# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import runpy: use this module through its namespace.
import runpy
# Import struct: reads binary PNG dimension fields with an explicit byte order.
import struct
# Import sys: provides process details and standard input/output streams.
import sys
# Import from types: SimpleNamespace (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.e2b_desktop: E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Import from crescendo_agent.vision: GroqVision (adapts screenshot observations to Groq vision
# requests); Screenshot (validates the PNG container and dimensions at the image boundary).
from crescendo_agent.vision import GroqVision, Screenshot
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant

# Set PNG to
# base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=').
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=")


# Define test_vision_sends_real_image_block_instead_of_stringifying_bytes with no parameters.
def test_vision_sends_real_image_block_instead_of_stringifying_bytes():
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.return_value to
    # SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',
    # message=SimpleNamespace(content='Visual code: ABC123'))]).
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        # Pass keyword finish_reason = 'stop'.
        finish_reason="stop", message=SimpleNamespace(content="Visual code: ABC123"))])
    # Set screenshot to Screenshot(PNG).
    screenshot = Screenshot(PNG)
    # Assert that GroqVision(client=client).describe(screenshot) equals 'Visual code: ABC123'. If
    # false, this check fails with AssertionError.
    assert GroqVision(client=client).describe(screenshot) == "Visual code: ABC123"
    # Set request to client.chat.completions.create.call_args.kwargs.
    request = client.chat.completions.create.call_args.kwargs
    # Set content to request['messages'][1]['content'].
    content = request["messages"][1]["content"]
    # Assert that content[0]['type'] equals 'text'. If false, this check fails with AssertionError.
    assert content[0]["type"] == "text"
    # Assert that 'ABC123' is not in content[0]['text']. If false, this check fails with
    # AssertionError.
    assert "ABC123" not in content[0]["text"]
    # Assert that content[1]['type'] equals 'image_url'. If false, this check fails with
    # AssertionError.
    assert content[1]["type"] == "image_url"
    # Set (prefix, data) to content[1]['image_url']['url'].split(',', 1).
    prefix, data = content[1]["image_url"]["url"].split(",", 1)
    # Assert that prefix equals 'data:image/png;base64'. If false, this check fails with
    # AssertionError.
    assert prefix == "data:image/png;base64"
    # Assert that base64.b64decode(data) equals PNG. If false, this check fails with AssertionError.
    assert base64.b64decode(data) == PNG
    # Assert that request['max_completion_tokens'] equals 512. If false, this check fails with
    # AssertionError.
    assert request["max_completion_tokens"] == 512
    # Assert that request['reasoning_effort'] equals 'none'. If false, this check fails with
    # AssertionError.
    assert request["reasoning_effort"] == "none"
    # Assert that 'tools' is not in request. If false, this check fails with AssertionError.
    assert "tools" not in request
    # Assert that screenshot.size equals the tuple (1, 1) (positional values). If false, this check
    # fails with AssertionError.
    assert screenshot.size == (1, 1)
    # Assert that repr(screenshot) equals 'Screenshot()'. If false, this check fails with
    # AssertionError.
    assert repr(screenshot) == "Screenshot()"


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("data", [b"", b"not a png" * 10, PNG * 100000,
                                   # Call struct.pack with the arguments shown.
                                   PNG[:16] + struct.pack(">II", 0, 10),
                                   # Call struct.pack with the arguments shown.
                                   PNG[:16] + struct.pack(">II", 9000, 10)])
# Define test_invalid_or_oversized_screenshot_is_rejected with parameters data.
def test_invalid_or_oversized_screenshot_is_rejected(data):
    # Use pytest.raises(ValueError); leave the context and run its cleanup when this block ends.
    with pytest.raises(ValueError):
        # Call Screenshot with data.
        Screenshot(data)


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("reason,text", [("length", "partial"), ("stop", ""), ("stop", None)])
# Define test_incomplete_or_empty_vision_response_is_rejected with parameters reason, text.
def test_incomplete_or_empty_vision_response_is_rejected(reason, text):
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.return_value to
    # SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason,
    # message=SimpleNamespace(content=text))]).
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        # Pass keyword finish_reason = reason.
        finish_reason=reason, message=SimpleNamespace(content=text))])
    # Use pytest.raises(ValueError, match='complete'); leave the context and run its cleanup when
    # this block ends.
    with pytest.raises(ValueError, match="complete"):
        # Call GroqVision(client=client).describe with Screenshot(PNG).
        GroqVision(client=client).describe(Screenshot(PNG))


# Define test_capture_requires_grant_before_touching_desktop with no parameters.
def test_capture_requires_grant_before_touching_desktop():
    # Set (page, provider) to (Mock(), Mock(return_value=PNG)).
    page, provider = Mock(), Mock(return_value=PNG)
    # Set desktop to E2BDesktop(page, Mock(), TaskGrant('no-capture', frozenset(), frozenset()),
    # screenshot_provider=provider).
    desktop = E2BDesktop(page, Mock(), TaskGrant("no-capture", frozenset(), frozenset()),
                         # Pass keyword screenshot_provider = provider.
                         screenshot_provider=provider)
    # Use pytest.raises(ValueError, match='not permitted'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(ValueError, match="not permitted"):
        # Call desktop.capture_screen with no arguments.
        desktop.capture_screen()
    # Call provider.assert_not_called with no arguments.
    provider.assert_not_called()
    # Call page.bring_to_front.assert_not_called with no arguments.
    page.bring_to_front.assert_not_called()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("provider_type", [bytes, bytearray])
# Define test_capture_foregrounds_page_before_calling_provider with parameters provider_type.
def test_capture_foregrounds_page_before_calling_provider(provider_type):
    # Set page to Mock().
    page = Mock()
    # Set payload to provider_type(PNG).
    payload = provider_type(PNG)
    # Define provider with no parameters.
    def provider():
        # Call page.bring_to_front.assert_called_once_with with no arguments.
        page.bring_to_front.assert_called_once_with()
        # Return payload.
        return payload
    # Set desktop to E2BDesktop(page, Mock(), TaskGrant('capture', frozenset({'screenshot'}),
    # frozenset()), screenshot_provider=provider).
    desktop = E2BDesktop(page, Mock(), TaskGrant("capture", frozenset({"screenshot"}), frozenset()),
                         # Pass keyword screenshot_provider = provider.
                         screenshot_provider=provider)
    # Set screenshot to desktop.capture_screen().
    screenshot = desktop.capture_screen()
    # Assert that screenshot.png equals PNG. If false, this check fails with AssertionError.
    assert screenshot.png == PNG
    # Assert that screenshot.png has type bytes (including subclasses). If false, this check fails
    # with AssertionError.
    assert isinstance(screenshot.png, bytes)
    # Check whether whether payload is an instance of bytearray.
    if isinstance(payload, bytearray):
        # Set payload[0] to 0.
        payload[0] = 0
        # Assert that screenshot.png equals PNG. If false, this check fails with AssertionError.
        assert screenshot.png == PNG


# Define test_invalid_bytearray_still_fails_screenshot_validation with no parameters.
def test_invalid_bytearray_still_fails_screenshot_validation():
    desktop = E2BDesktop(Mock(), Mock(), TaskGrant("capture", frozenset({"screenshot"}), frozenset()),
                         # Pass keyword screenshot_provider = lambda : bytearray(b'not a PNG').
                         screenshot_provider=lambda: bytearray(b"not a PNG"))
    # Use pytest.raises(ValueError, match='PNG'); leave the context and run its cleanup when this
    # block ends.
    with pytest.raises(ValueError, match="PNG"):
        # Call desktop.capture_screen with no arguments.
        desktop.capture_screen()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("model_fails", [False, True])
# Define test_vision_demo_cleans_up_before_output_and_on_model_failure with parameters monkeypatch,
# capsys, model_fails.
def test_vision_demo_cleans_up_before_output_and_on_model_failure(monkeypatch, capsys, model_fails):
    # Call monkeypatch.setenv with 'E2B_API_KEY', 'offline-e2b-key'.
    monkeypatch.setenv("E2B_API_KEY", "offline-e2b-key")
    # Call monkeypatch.setenv with 'GROQ_API_KEY', 'offline-groq-key'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-key")
    # Call monkeypatch.setattr with sys, 'argv', ['e2b_vision_demo.py'].
    monkeypatch.setattr(sys, "argv", ["e2b_vision_demo.py"])
    # Call monkeypatch.setattr with 'secrets.token_hex', a function that returns 'abc123' when
    # called.
    monkeypatch.setattr("secrets.token_hex", lambda n: "abc123")
    # Set closed to an empty list.
    closed = []
    # Set desktop to Mock().
    desktop = Mock()
    # Set desktop.capture_screen.return_value to Screenshot(PNG).
    desktop.capture_screen.return_value = Screenshot(PNG)

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define fake_open with parameters grant.
    def fake_open(grant):
        # Assert that grant.allowed_hosts equals frozenset(). If false, this check fails with
        # AssertionError.
        assert grant.allowed_hosts == frozenset()
        # Assert that grant.allowed_tools equals frozenset({'screenshot'}). If false, this check
        # fails with AssertionError.
        assert grant.allowed_tools == frozenset({"screenshot"})
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give desktop to the caller and pause here until execution resumes.
            yield desktop
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Append True to closed.
            closed.append(True)

    # Set model to Mock().
    model = Mock()
    # Set model.model to 'test-vision-model'.
    model.model = "test-vision-model"
    # Set model.describe.side_effect to RuntimeError('Model unavailable') if model_fails, otherwise
    # None.
    model.describe.side_effect = RuntimeError("Model unavailable") if model_fails else None
    # Set model.describe.return_value to 'Visual code: ABC123. The desktop shows Ready.'.
    model.describe.return_value = "Visual code: ABC123. The desktop shows Ready."
    # Call monkeypatch.setattr with 'crescendo_agent.e2b_desktop.open_e2b_desktop', fake_open.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    # Call monkeypatch.setattr with 'crescendo_agent.vision.GroqVision', a function that returns
    # model when called.
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: model)
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'e2b_vision_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_demo.py"
    # Check whether model_fails.
    if model_fails:
        # Use pytest.raises(RuntimeError, match='Model unavailable'); leave the context and run its
        # cleanup when this block ends.
        with pytest.raises(RuntimeError, match="Model unavailable"):
            # Call runpy.run_path with script converted to a string.
            runpy.run_path(str(script), run_name="__main__")
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Call runpy.run_path with script converted to a string.
        runpy.run_path(str(script), run_name="__main__")
    # Assert that closed equals a new list containing True. If false, this check fails with
    # AssertionError.
    assert closed == [True]
    # Call model.describe.assert_called_once_with with Screenshot(PNG).
    model.describe.assert_called_once_with(Screenshot(PNG))
    # Set output to capsys.readouterr().out.
    output = capsys.readouterr().out
    # Assert that 'offline-e2b-key' is not in output AND 'offline-groq-key' is not in output. If
    # false, this check fails with AssertionError.
    assert "offline-e2b-key" not in output and "offline-groq-key" not in output
    # Assert that 'data:image' is not in output. If false, this check fails with AssertionError.
    assert "data:image" not in output
    # Check whether model_fails.
    if model_fails:
        # Assert that 'PASS' is not in output. If false, this check fails with AssertionError.
        assert "PASS" not in output
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Assert that 'PASS: model read the code' is in output. If false, this check fails with
        # AssertionError.
        assert "PASS: model read the code" in output


# Define test_vision_client_does_not_retry_provider_error with no parameters.
def test_vision_client_does_not_retry_provider_error():
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.side_effect to RuntimeError('provider unavailable').
    client.chat.completions.create.side_effect = RuntimeError("provider unavailable")
    # Use pytest.raises(RuntimeError, match='provider unavailable'); leave the context and run its
    # cleanup when this block ends.
    with pytest.raises(RuntimeError, match="provider unavailable"):
        # Call GroqVision(client=client).describe with Screenshot(PNG).
        GroqVision(client=client).describe(Screenshot(PNG))
    # Assert that client.chat.completions.create.call_count equals 1. If false, this check fails
    # with AssertionError.
    assert client.chat.completions.create.call_count == 1


# Define test_default_vision_client_has_timeout_and_no_sdk_retries with parameters monkeypatch.
def test_default_vision_client_has_timeout_and_no_sdk_retries(monkeypatch):
    # Set client_factory to Mock().
    client_factory = Mock()
    # Call monkeypatch.setattr with 'groq.Groq', client_factory.
    monkeypatch.setattr("groq.Groq", client_factory)
    # Call GroqVision with no arguments.
    GroqVision()
    # Call client_factory.assert_called_once_with with no arguments.
    client_factory.assert_called_once_with(timeout=30.0, max_retries=0)
