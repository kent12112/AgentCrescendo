"""Screenshot downscaling and bounded provider rate-limit handling."""
# Import from io: BytesIO (stores image bytes in an in-memory file-like buffer).
from io import BytesIO
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import from types: SimpleNamespace as NS (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace as NS
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import from PIL: Image (opens and resizes PNG images using Pillow).
from PIL import Image
# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.vision: GroqVision (adapts screenshot observations to Groq vision
# requests); RateLimited (carries only a retry delay, without leaking provider error text);
# Screenshot (validates the PNG container and dimensions at the image boundary); downscale (shrinks
# the PNG before both saving and model submission); rate_limit_delay (a dependency used below).
from crescendo_agent.vision import GroqVision, RateLimited, Screenshot, downscale, rate_limit_delay
# Import from crescendo_agent.vision_loop: MAX_RATE_LIMIT_WAIT (a dependency used below);
# run_vision_agent (runs the bounded screenshot/proposal/authorization/action loop).
from crescendo_agent.vision_loop import MAX_RATE_LIMIT_WAIT, run_vision_agent
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall

# Set GRANT to TaskGrant('vision', frozenset({'screenshot', 'scroll', 'finish'}), frozenset()).
GRANT = TaskGrant("vision", frozenset({"screenshot", "scroll", "finish"}), frozenset())
# Set FINISH to ToolCall('finish', {'answer': '617565'}).
FINISH = ToolCall("finish", {"answer": "617565"})


# Define png with parameters width, height.
def png(width, height):
    # Set output to BytesIO().
    output = BytesIO()
    # Call Image.new('RGB', (width, height), 'white').save with output.
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    # Return Screenshot(output.getvalue()).
    return Screenshot(output.getvalue())


# Define test_downscale_keeps_aspect_ratio_and_leaves_small_images_alone with no parameters.
def test_downscale_keeps_aspect_ratio_and_leaves_small_images_alone():
    # Set small to png(640, 480).
    small = png(640, 480)
    # Assert that downscale(small, 768) is small. If false, this check fails with AssertionError.
    assert downscale(small, 768) is small
    # Set scaled to downscale(png(1024, 768), 768).
    scaled = downscale(png(1024, 768), 768)
    # Assert that scaled.size equals the tuple (768, 576) (positional values). If false, this check
    # fails with AssertionError.
    assert scaled.size == (768, 576)


# Define test_loop_saves_and_sends_the_same_downscaled_image with no parameters.
def test_loop_saves_and_sends_the_same_downscaled_image():
    # Set desktop to Mock().
    desktop = Mock()
    # Set desktop.capture_screen.return_value to png(1024, 768).
    desktop.capture_screen.return_value = png(1024, 768)
    # Set (saved, sent) to ([], []).
    saved, sent = [], []
    # Set model to Mock().
    model = Mock()
    # Set model.decide.side_effect to a function that returns (sent.append(image), FINISH)[1] when
    # called.
    model.decide.side_effect = lambda image, transcript: (sent.append(image), FINISH)[1]
    # Call run_vision_agent with 'g', GRANT, desktop, model.
    run_vision_agent("g", GRANT, desktop, model, max_image_width=768,
                     on_screenshot=lambda step, image: saved.append(image))
    # Assert that saved[0].size equals the tuple (768, 576) (positional values). If false, this
    # check fails with AssertionError.
    assert saved[0].size == (768, 576)
    # Assert that saved[0] is sent[0]. If false, this check fails with AssertionError.
    assert saved[0] is sent[0]


# Define Throttled as a subclass of Exception.
class Throttled(Exception):
    # Set status_code to 429.
    status_code = 429

    # Define __init__ with parameters self, message, headers.
    def __init__(self, message="Rate limit for org_SECRET123. Please try again in 6.6s.", headers=None):
        # Call super().__init__ with message.
        super().__init__(message)
        # Set self.response to NS(headers=headers or {}).
        self.response = NS(headers=headers or {})


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("error,expected", [
    # Pass keyword headers = a new dictionary with keys 'retry-after'.
    (Throttled(headers={"retry-after": "3"}), 3.0),
    # Call Throttled with no arguments.
    (Throttled(), 6.6),
    # Pass keyword message = 'slow down'.
    (Throttled(message="slow down"), 10.0),
    # Call ValueError with the arguments shown.
    (ValueError("not a rate limit"), None),
])
# Define test_rate_limit_delay with parameters error, expected.
def test_rate_limit_delay(error, expected):
    # Assert that rate_limit_delay(error) equals expected. If false, this check fails with
    # AssertionError.
    assert rate_limit_delay(error) == expected


# Define test_groq_rate_limit_becomes_sanitized_rate_limited with no parameters.
def test_groq_rate_limit_becomes_sanitized_rate_limited():
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.side_effect to Throttled().
    client.chat.completions.create.side_effect = Throttled()
    # Use pytest.raises(RateLimited) as raised; leave the context and run its cleanup when this
    # block ends.
    with pytest.raises(RateLimited) as raised:
        # Call GroqVision(client=client).decide with png(8, 8), an empty list.
        GroqVision(client=client).decide(png(8, 8), [])
    # Assert that raised.value.retry_after equals 6.6. If false, this check fails with
    # AssertionError.
    assert raised.value.retry_after == 6.6
    # Assert that 'org_' is not in str(raised.value). If false, this check fails with
    # AssertionError.
    assert "org_" not in str(raised.value)
    # Assert that raised.value.__cause__ is None (no value) AND raised.value.__suppress_context__.
    # If false, this check fails with AssertionError.
    assert raised.value.__cause__ is None and raised.value.__suppress_context__


# Define test_other_provider_errors_still_propagate with no parameters.
def test_other_provider_errors_still_propagate():
    # Set client to Mock().
    client = Mock()
    # Set client.chat.completions.create.side_effect to RuntimeError('network down').
    client.chat.completions.create.side_effect = RuntimeError("network down")
    # Use pytest.raises(RuntimeError, match='network down'); leave the context and run its cleanup
    # when this block ends.
    with pytest.raises(RuntimeError, match="network down"):
        # Call GroqVision(client=client).decide with png(8, 8), an empty list.
        GroqVision(client=client).decide(png(8, 8), [])


# Define Clock.
class Clock:
    # Define __init__ with parameters self.
    def __init__(self):
        # Set self.now to 0.0.
        self.now = 0.0

    # Define __call__ with parameters self.
    def __call__(self):
        # Return self.now.
        return self.now

    # Define sleep with parameters self, seconds.
    def sleep(self, seconds):
        # Update self.now using its previous value plus seconds.
        self.now += seconds


# Define test_loop_waits_once_then_retries_same_screenshot with no parameters.
def test_loop_waits_once_then_retries_same_screenshot():
    # Set (clock, desktop, model) to (Clock(), Mock(), Mock()).
    clock, desktop, model = Clock(), Mock(), Mock()
    # Set desktop.capture_screen.return_value to png(8, 8).
    desktop.capture_screen.return_value = png(8, 8)
    # Set model.decide.side_effect to [RateLimited(5), FINISH].
    model.decide.side_effect = [RateLimited(5), FINISH]
    # Set waits to an empty list.
    waits = []
    # Set result to run_vision_agent('g', GRANT, desktop, model, clock=clock, sleep=clock.sleep,
    # on_rate_limit=lambda step, seconds: waits.append((step, seconds))).
    result = run_vision_agent("g", GRANT, desktop, model, clock=clock, sleep=clock.sleep,
                              on_rate_limit=lambda step, seconds: waits.append((step, seconds)))
    # Assert that result.status equals 'finished' AND clock.now equals 5. If false, this check fails
    # with AssertionError.
    assert result.status == "finished" and clock.now == 5
    # Assert that waits equals a new list containing the tuple (1, 5) (positional values). If false,
    # this check fails with AssertionError.
    assert waits == [(1, 5)]
    # Set (first, second) to model.decide.call_args_list.
    first, second = model.decide.call_args_list
    # Assert that first.args[0] is second.args[0]. If false, this check fails with AssertionError.
    assert first.args[0] is second.args[0]
    # Assert that not (any(('rate limit' in entry.text.lower() for entry in result.transcript))). If
    # false, this check fails with AssertionError.
    assert not any("rate limit" in entry.text.lower() for entry in result.transcript)


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("delays,capture_seconds", [
    # Add this item to the surrounding list: ([MAX_RATE_LIMIT_WAIT + 1], 0), # asks for too long a
    # wait.
    ([MAX_RATE_LIMIT_WAIT + 1], 0),   # asks for too long a wait
    # Add this item to the surrounding list: ([5], 117), # capture used 117 s of 120; a 5 s wait
    # would pass the deadline.
    ([5], 117),                        # capture used 117 s of 120; a 5 s wait would pass the deadline
    # Add this item to the surrounding list: ([5, 5], 0), # still throttled after one retry.
    ([5, 5], 0),                       # still throttled after one retry
])
# Define test_loop_stops_cleanly_when_rate_limit_cannot_be_absorbed with parameters delays,
# capture_seconds.
def test_loop_stops_cleanly_when_rate_limit_cannot_be_absorbed(delays, capture_seconds):
    # Set (clock, desktop, model) to (Clock(), Mock(), Mock()).
    clock, desktop, model = Clock(), Mock(), Mock()
    # Define capture with no parameters.
    def capture():
        # Call clock.sleep with capture_seconds.
        clock.sleep(capture_seconds)
        # Return png(8, 8).
        return png(8, 8)
    # Set desktop.capture_screen.side_effect to capture.
    desktop.capture_screen.side_effect = capture
    # Set model.decide.side_effect to [RateLimited(delay) for delay in delays].
    model.decide.side_effect = [RateLimited(delay) for delay in delays]
    # Set result to run_vision_agent('g', GRANT, desktop, model, clock=clock, sleep=clock.sleep).
    result = run_vision_agent("g", GRANT, desktop, model, clock=clock, sleep=clock.sleep)
    # Assert that result.status equals 'rate_limited'. If false, this check fails with
    # AssertionError.
    assert result.status == "rate_limited"
    # Call desktop.scroll.assert_not_called with no arguments.
    desktop.scroll.assert_not_called()
    # Assert that clock.now is at most capture_seconds plus MAX_RATE_LIMIT_WAIT. If false, this
    # check fails with AssertionError.
    assert clock.now <= capture_seconds + MAX_RATE_LIMIT_WAIT
