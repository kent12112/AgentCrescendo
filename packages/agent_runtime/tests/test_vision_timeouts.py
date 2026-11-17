"""Timeout recovery must retry inference without replaying desktop actions."""
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import Mock

from PIL import Image
import pytest

from crescendo_agent.vision import GroqVision, ModelTimedOut, ModelUnavailable, RateLimited, Screenshot
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import ScreenArea, TaskGrant, ToolCall


GRANT = TaskGrant("timeouts", frozenset({"screenshot", "click", "scroll", "finish"}), frozenset())
CLICK = ToolCall("click", {"x": 317, "y": 602})
FINISH = ToolCall("finish", {"answer": "Massachusetts"})


def desktop_fixture():
    output = BytesIO()
    Image.new("RGB", (1024, 768), "white").save(output, format="PNG")
    desktop = Mock()
    desktop.capture_screen.return_value = Screenshot(output.getvalue())
    desktop.click_area.return_value = ScreenArea(0, 114, 1024, 700)
    desktop.click.return_value = "The click opened https://en.wikipedia.org/wiki/Massachusetts."
    return desktop


class Clock:
    now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_actual_sdk_read_timeout_is_sanitized_and_sdk_does_not_retry():
    groq = pytest.importorskip("groq")
    import httpx

    requests = []

    def fail(request):
        requests.append(request)
        raise httpx.ReadTimeout("sensitive transport diagnostics", request=request)

    with groq.Groq(api_key="test-only", max_retries=0,
                   http_client=httpx.Client(transport=httpx.MockTransport(fail))) as client:
        model = GroqVision(client=client)
        with pytest.raises(ModelTimedOut) as caught:
            model.decide(desktop_fixture().capture_screen(), [])
    assert len(requests) == 1
    assert str(caught.value) == "The model request timed out."
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_connection_errors_remain_distinct_from_timeouts():
    groq = pytest.importorskip("groq")
    import httpx

    error = groq.APIConnectionError(request=httpx.Request("POST", "https://example.com/"))
    client = Mock()
    client.chat.completions.create.side_effect = error
    with pytest.raises(groq.APIConnectionError) as caught:
        GroqVision(client=client).decide(desktop_fixture().capture_screen(), [])
    assert caught.value is error


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_actual_sdk_server_errors_are_sanitized_and_respect_retry_after(status):
    groq = pytest.importorskip("groq")
    import httpx

    def unavailable(request):
        return httpx.Response(status, headers={"retry-after": "3"},
                              json={"error": {"message": "private provider diagnostics"}})

    with groq.Groq(api_key="test-only", max_retries=0,
                   http_client=httpx.Client(transport=httpx.MockTransport(unavailable))) as client:
        with pytest.raises(ModelUnavailable) as caught:
            GroqVision(client=client).decide(desktop_fixture().capture_screen(), [])
    assert caught.value.retry_after == 3
    assert "private" not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_configurable_request_timeout_preserves_disabled_sdk_retries(monkeypatch):
    groq = pytest.importorskip("groq")
    factory = Mock()
    monkeypatch.setattr(groq, "Groq", factory)
    GroqVision(request_timeout=45)
    factory.assert_called_once_with(timeout=45, max_retries=0)


@pytest.mark.parametrize("seconds", [0, -1, 61, float("inf"), float("nan"), "30", True])
def test_invalid_request_timeout_is_rejected_before_client_creation(seconds):
    with pytest.raises(ValueError, match="request_timeout"):
        GroqVision(client=Mock(), request_timeout=seconds)


def test_timeout_retries_identical_input_then_executes_one_click():
    desktop, model, clock = desktop_fixture(), Mock(), Clock()
    inputs, notifications = [], []

    def decide(image, transcript):
        inputs.append((image, list(transcript)))
        if len(inputs) == 1:
            clock.sleep(30)
            raise ModelTimedOut("private diagnostics must not enter the trace")
        return CLICK

    model.decide.side_effect = decide
    result = run_vision_agent("click", GRANT, desktop, model, max_steps=1,
                              clock=clock, sleep=clock.sleep,
                              on_model_timeout=notifications.append)
    assert result.status == "step_limit"
    assert inputs[0] == inputs[1] and inputs[0][0] is inputs[1][0]
    assert notifications == [1]
    desktop.capture_screen.assert_called_once_with()
    desktop.click.assert_called_once_with(317, 602)
    assert len([e for e in result.transcript if e.kind == "model_error"]) == 1
    assert all("private diagnostics" not in e.text for e in result.transcript)


def test_repeated_timeouts_stop_with_trace_and_no_desktop_action():
    desktop, model = desktop_fixture(), Mock()
    model.decide.side_effect = [ModelTimedOut(), ModelTimedOut(), FINISH]
    result = run_vision_agent("click", GRANT, desktop, model)
    assert result.status == "model_timeout" and result.answer is None
    assert model.decide.call_count == 2
    desktop.click.assert_not_called()
    desktop.scroll.assert_not_called()
    assert len([e for e in result.transcript if e.kind == "model_error"]) == 2
    assert not [e for e in result.transcript if e.kind == "action"]


def test_timeout_after_successful_click_does_not_replay_click():
    desktop, model = desktop_fixture(), Mock()
    model.decide.side_effect = [CLICK, ModelTimedOut(), ModelTimedOut(), FINISH]
    result = run_vision_agent("click then finish", GRANT, desktop, model)
    assert result.status == "model_timeout" and model.decide.call_count == 3
    desktop.click.assert_called_once_with(317, 602)


@pytest.mark.parametrize("failures, expected", [
    ([RateLimited(5), ModelTimedOut()], "model_timeout"),
    ([ModelTimedOut(), RateLimited(5)], "rate_limited"),
    ([ModelTimedOut(), ModelUnavailable()], "model_unavailable"),
    ([ModelUnavailable(), ModelTimedOut()], "model_timeout"),
    ([ModelUnavailable(), ModelUnavailable()], "model_unavailable"),
])
def test_timeout_and_throttle_share_one_retry_budget(failures, expected):
    desktop, model, clock = desktop_fixture(), Mock(), Clock()
    model.decide.side_effect = failures + [CLICK]
    result = run_vision_agent("click", GRANT, desktop, model, clock=clock, sleep=clock.sleep)
    assert result.status == expected and model.decide.call_count == 2
    desktop.click.assert_not_called()


def test_unavailable_service_backs_off_once_then_recovers():
    desktop, model, clock, notices = desktop_fixture(), Mock(), Clock(), []
    model.decide.side_effect = [ModelUnavailable(2), FINISH]
    result = run_vision_agent("g", GRANT, desktop, model, clock=clock, sleep=clock.sleep,
                              on_model_unavailable=lambda step, wait: notices.append((step, wait)))
    assert result.status == "finished" and clock.now == 2
    assert notices == [(1, 2)] and model.decide.call_count == 2


def test_server_requested_wait_cannot_exceed_remaining_deadline():
    desktop, model, clock = desktop_fixture(), Mock(), Clock()
    model.decide.side_effect = [ModelUnavailable(60), CLICK]
    result = run_vision_agent("click", GRANT, desktop, model, clock=clock, sleep=clock.sleep,
                              max_rate_limit_wait=60, deadline_seconds=30)
    assert result.status == "model_unavailable" and clock.now == 0
    model.decide.assert_called_once()
    desktop.click.assert_not_called()
    assert [e for e in result.transcript if e.kind == "model_error"]


def test_timeout_at_deadline_admits_no_retry():
    desktop, model, clock = desktop_fixture(), Mock(), Clock()

    def decide(image, transcript):
        clock.sleep(120)
        raise ModelTimedOut()

    model.decide.side_effect = decide
    result = run_vision_agent("click", GRANT, desktop, model, clock=clock, sleep=clock.sleep)
    assert result.status == "deadline"
    model.decide.assert_called_once()
    desktop.click.assert_not_called()


def test_deadline_is_rechecked_after_retry_callback():
    desktop, model, clock = desktop_fixture(), Mock(), Clock()
    model.decide.side_effect = [ModelTimedOut(), CLICK]
    result = run_vision_agent("click", GRANT, desktop, model, clock=clock, sleep=clock.sleep,
                              on_model_timeout=lambda step: clock.sleep(120))
    assert result.status == "deadline"
    model.decide.assert_called_once()
    desktop.click.assert_not_called()


@pytest.mark.parametrize("failure, status, message", [
    (ModelTimedOut, "model_timeout", "MODEL TIMEOUT"),
    (lambda: ModelUnavailable(0), "model_unavailable", "MODEL UNAVAILABLE"),
])
def test_click_demo_saves_provider_failure_and_closes_desktop(tmp_path, monkeypatch, capsys,
                                                            failure, status, message):
    script = Path(__file__).resolve().parents[3] / "scripts" / "e2b_click_demo.py"
    main = runpy.run_path(str(script))["main"]
    desktop, model, cleanup = desktop_fixture(), Mock(), []
    desktop.visible_links.return_value = []
    desktop.page.url = "https://en.wikipedia.org/wiki/Boston"
    desktop.last_navigation_status, desktop.last_navigation_retry_after = 200, None
    desktop.visited, desktop.blocked_requests, desktop.closed_pages = [desktop.page.url], [], []
    desktop.page.locator.return_value.count.return_value = 1
    model.model = "test-model"
    model.decide.side_effect = [failure(), failure()]

    @contextmanager
    def open_desktop(*args, **kwargs):
        try:
            yield desktop
        finally:
            cleanup.append("closed")

    monkeypatch.setitem(main.__globals__, "load_local_env", lambda: None)
    monkeypatch.setitem(main.__globals__, "open_e2b_desktop", open_desktop)
    monkeypatch.setitem(main.__globals__, "GroqVision", lambda *args, **kwargs: model)
    monkeypatch.setenv("E2B_API_KEY", "test-only")
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    monkeypatch.setattr(sys, "argv", [str(script), "--save-screenshots"])
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1 and cleanup == ["closed"]
    result_file, = tmp_path.glob(".demo-artifacts/click-*/result.json")
    result = json.loads(result_file.read_text())
    assert result["status"] == status and result["request_timeout"] == 45
    assert result_file.with_name("step-01.png").exists()
    assert message in capsys.readouterr().out
    desktop.click.assert_not_called()
