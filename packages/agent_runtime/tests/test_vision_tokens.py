"""Screenshot downscaling and bounded provider rate-limit handling."""
from io import BytesIO
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock

from PIL import Image
import pytest

from crescendo_agent.vision import GroqVision, RateLimited, Screenshot, downscale, rate_limit_delay
from crescendo_agent.vision_loop import MAX_RATE_LIMIT_WAIT, run_vision_agent
from crescendo_security.policy import TaskGrant, ToolCall

GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())
FINISH = ToolCall("finish", {"answer": "617565"})


def png(width, height):
    output = BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return Screenshot(output.getvalue())


def test_downscale_keeps_aspect_ratio_and_leaves_small_images_alone():
    small = png(640, 480)
    assert downscale(small, 768) is small
    scaled = downscale(png(1024, 768), 768)
    assert scaled.size == (768, 576)


def test_loop_saves_and_sends_the_same_downscaled_image():
    desktop = Mock()
    desktop.capture_screen.return_value = png(1024, 768)
    saved, sent = [], []
    model = Mock()
    model.decide.side_effect = lambda image, transcript: (sent.append(image), FINISH)[1]
    run_vision_agent("g", GRANT, desktop, model, max_image_width=768,
                     on_screenshot=lambda step, image: saved.append(image))
    assert saved[0].size == (768, 576)
    assert saved[0] is sent[0]


class Throttled(Exception):
    status_code = 429

    def __init__(self, message="Rate limit for org_SECRET123. Please try again in 6.6s.", headers=None):
        super().__init__(message)
        self.response = NS(headers=headers or {})


@pytest.mark.parametrize("error,expected", [
    (Throttled(headers={"retry-after": "3"}), 3.0),
    (Throttled(), 6.6),
    (Throttled(message="slow down"), 10.0),
    (ValueError("not a rate limit"), None),
])
def test_rate_limit_delay(error, expected):
    assert rate_limit_delay(error) == expected


def test_groq_rate_limit_becomes_sanitized_rate_limited():
    client = Mock()
    client.chat.completions.create.side_effect = Throttled()
    with pytest.raises(RateLimited) as raised:
        GroqVision(client=client).decide(png(8, 8), [])
    assert raised.value.retry_after == 6.6
    assert "org_" not in str(raised.value)
    assert raised.value.__cause__ is None and raised.value.__suppress_context__


def test_other_provider_errors_still_propagate():
    client = Mock()
    client.chat.completions.create.side_effect = RuntimeError("network down")
    with pytest.raises(RuntimeError, match="network down"):
        GroqVision(client=client).decide(png(8, 8), [])


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_loop_waits_once_then_retries_same_screenshot():
    clock, desktop, model = Clock(), Mock(), Mock()
    desktop.capture_screen.return_value = png(8, 8)
    model.decide.side_effect = [RateLimited(5), FINISH]
    waits = []
    result = run_vision_agent("g", GRANT, desktop, model, clock=clock, sleep=clock.sleep,
                              on_rate_limit=lambda step, seconds: waits.append((step, seconds)))
    assert result.status == "finished" and clock.now == 5
    assert waits == [(1, 5)]
    first, second = model.decide.call_args_list
    assert first.args[0] is second.args[0]
    assert not any("rate limit" in entry.text.lower() for entry in result.transcript)


@pytest.mark.parametrize("delays,capture_seconds", [
    ([MAX_RATE_LIMIT_WAIT + 1], 0),   # asks for too long a wait
    ([5], 117),                        # capture used 117 s of 120; a 5 s wait would pass the deadline
    ([5, 5], 0),                       # still throttled after one retry
])
def test_loop_stops_cleanly_when_rate_limit_cannot_be_absorbed(delays, capture_seconds):
    clock, desktop, model = Clock(), Mock(), Mock()
    def capture():
        clock.sleep(capture_seconds)
        return png(8, 8)
    desktop.capture_screen.side_effect = capture
    model.decide.side_effect = [RateLimited(delay) for delay in delays]
    result = run_vision_agent("g", GRANT, desktop, model, clock=clock, sleep=clock.sleep)
    assert result.status == "rate_limited"
    desktop.scroll.assert_not_called()
    assert clock.now <= capture_seconds + MAX_RATE_LIMIT_WAIT
