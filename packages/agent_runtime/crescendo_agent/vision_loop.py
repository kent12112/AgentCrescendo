"""Bounded screenshot -> proposal -> gateway -> scroll/finish execution."""
import json
import math
import time

from crescendo_security.policy import Decision, authorize

from .loop import AgentState, RunResult
from .model import Entry
from .vision import valid_finish


def run_vision_agent(goal, grant, desktop, model, *, max_steps=5,
                     deadline_seconds=120.0, clock=time.monotonic,
                     on_screenshot=None, finish_validator=None) -> RunResult:
    if type(max_steps) is not int or not 1 <= max_steps <= 10:
        raise ValueError("max_steps must be an integer from 1 to 10.")
    if not math.isfinite(deadline_seconds) or not 0 < deadline_seconds <= 120:
        raise ValueError("deadline_seconds must be positive and at most 120.")
    state = AgentState(goal, grant)
    state.transcript.append(Entry("goal", goal))
    deadline = clock() + deadline_seconds
    for step in range(max_steps):
        if clock() >= deadline:
            return state.stop("deadline")
        screenshot = desktop.capture_screen()
        if on_screenshot is not None:
            on_screenshot(step + 1, screenshot)
        state.transcript.append(Entry("observation", f"Current screenshot captured: {screenshot.size}. Image supplied separately."))
        if clock() >= deadline:
            return state.stop("deadline")
        call = model.decide(screenshot, state.transcript)
        state.transcript.append(Entry("action", json.dumps({"tool": call.name, "args": dict(call.args)})))
        # A model request already in flight can overrun; admit no action afterward.
        if clock() >= deadline:
            return state.stop("deadline")
        decision = authorize(grant, call)
        if decision.allowed and call.name not in {"scroll", "finish"}:
            decision = Decision(False, "This vision loop supports only scroll and finish.")
        if decision.allowed and call.name == "finish" and not valid_finish(dict(call.args)):
            decision = Decision(False, "finish requires one nonblank answer of at most 2000 characters.")
        if decision.allowed and call.name == "finish" and finish_validator is not None:
            reason = finish_validator(call.args["answer"])
            if reason is not None:
                decision = Decision(False, reason)
        if not decision.allowed:
            state.denied.append((call, decision))
            state.transcript.append(Entry("denied", decision.reason))
            continue
        if call.name == "finish":
            return state.stop("finished", call.args["answer"])
        desktop.scroll(call.args["direction"], call.args["amount"])
        state.transcript.append(Entry("observation", "Authorized scroll completed. Inspect the next screenshot for its effect."))
    return state.stop("step_limit")
