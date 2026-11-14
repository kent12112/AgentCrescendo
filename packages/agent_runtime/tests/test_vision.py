import base64
from contextlib import contextmanager
from pathlib import Path
import runpy
import struct
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_agent.vision import GroqVision, Screenshot
from crescendo_security.policy import TaskGrant

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1sAAAAASUVORK5CYII=")


def test_vision_sends_real_image_block_instead_of_stringifying_bytes():
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        finish_reason="stop", message=SimpleNamespace(content="Visual code: ABC123"))])
    screenshot = Screenshot(PNG)
    assert GroqVision(client=client).describe(screenshot) == "Visual code: ABC123"
    request = client.chat.completions.create.call_args.kwargs
    content = request["messages"][1]["content"]
    assert content[0]["type"] == "text"
    assert "ABC123" not in content[0]["text"]
    assert content[1]["type"] == "image_url"
    prefix, data = content[1]["image_url"]["url"].split(",", 1)
    assert prefix == "data:image/png;base64"
    assert base64.b64decode(data) == PNG
    assert request["max_completion_tokens"] == 512
    assert request["reasoning_effort"] == "none"
    assert "tools" not in request
    assert screenshot.size == (1, 1)
    assert repr(screenshot) == "Screenshot()"


@pytest.mark.parametrize("data", [b"", b"not a png" * 10, PNG * 100000,
                                   PNG[:16] + struct.pack(">II", 0, 10),
                                   PNG[:16] + struct.pack(">II", 9000, 10)])
def test_invalid_or_oversized_screenshot_is_rejected(data):
    with pytest.raises(ValueError):
        Screenshot(data)


@pytest.mark.parametrize("reason,text", [("length", "partial"), ("stop", ""), ("stop", None)])
def test_incomplete_or_empty_vision_response_is_rejected(reason, text):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        finish_reason=reason, message=SimpleNamespace(content=text))])
    with pytest.raises(ValueError, match="complete"):
        GroqVision(client=client).describe(Screenshot(PNG))


def test_capture_requires_grant_before_touching_desktop():
    page, provider = Mock(), Mock(return_value=PNG)
    desktop = E2BDesktop(page, Mock(), TaskGrant("no-capture", frozenset(), frozenset()),
                         screenshot_provider=provider)
    with pytest.raises(ValueError, match="not permitted"):
        desktop.capture_screen()
    provider.assert_not_called()
    page.bring_to_front.assert_not_called()


@pytest.mark.parametrize("provider_type", [bytes, bytearray])
def test_capture_foregrounds_page_before_calling_provider(provider_type):
    page = Mock()
    payload = provider_type(PNG)
    def provider():
        page.bring_to_front.assert_called_once_with()
        return payload
    desktop = E2BDesktop(page, Mock(), TaskGrant("capture", frozenset({"screenshot"}), frozenset()),
                         screenshot_provider=provider)
    screenshot = desktop.capture_screen()
    assert screenshot.png == PNG
    assert isinstance(screenshot.png, bytes)
    if isinstance(payload, bytearray):
        payload[0] = 0
        assert screenshot.png == PNG


def test_invalid_bytearray_still_fails_screenshot_validation():
    desktop = E2BDesktop(Mock(), Mock(), TaskGrant("capture", frozenset({"screenshot"}), frozenset()),
                         screenshot_provider=lambda: bytearray(b"not a PNG"))
    with pytest.raises(ValueError, match="PNG"):
        desktop.capture_screen()


@pytest.mark.parametrize("model_fails", [False, True])
def test_vision_demo_cleans_up_before_output_and_on_model_failure(monkeypatch, capsys, model_fails):
    monkeypatch.setenv("E2B_API_KEY", "offline-e2b-key")
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-key")
    monkeypatch.setattr(sys, "argv", ["e2b_vision_demo.py"])
    monkeypatch.setattr("secrets.token_hex", lambda n: "abc123")
    closed = []
    desktop = Mock()
    desktop.capture_screen.return_value = Screenshot(PNG)

    @contextmanager
    def fake_open(grant):
        assert grant.allowed_hosts == frozenset()
        assert grant.allowed_tools == frozenset({"screenshot"})
        try:
            yield desktop
        finally:
            closed.append(True)

    model = Mock()
    model.model = "test-vision-model"
    model.describe.side_effect = RuntimeError("Model unavailable") if model_fails else None
    model.describe.return_value = "Visual code: ABC123. The desktop shows Ready."
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_open)
    monkeypatch.setattr("crescendo_agent.vision.GroqVision", lambda name: model)
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_vision_demo.py"
    if model_fails:
        with pytest.raises(RuntimeError, match="Model unavailable"):
            runpy.run_path(str(script), run_name="__main__")
    else:
        runpy.run_path(str(script), run_name="__main__")
    assert closed == [True]
    model.describe.assert_called_once_with(Screenshot(PNG))
    output = capsys.readouterr().out
    assert "offline-e2b-key" not in output and "offline-groq-key" not in output
    assert "data:image" not in output
    if model_fails:
        assert "PASS" not in output
    else:
        assert "PASS: model read the code" in output


def test_vision_client_does_not_retry_provider_error():
    client = Mock()
    client.chat.completions.create.side_effect = RuntimeError("provider unavailable")
    with pytest.raises(RuntimeError, match="provider unavailable"):
        GroqVision(client=client).describe(Screenshot(PNG))
    assert client.chat.completions.create.call_count == 1


def test_default_vision_client_has_timeout_and_no_sdk_retries(monkeypatch):
    client_factory = Mock()
    monkeypatch.setattr("groq.Groq", client_factory)
    GroqVision()
    client_factory.assert_called_once_with(timeout=30.0, max_retries=0)
