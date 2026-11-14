# ANNOTATED READING COPY — not executed, not imported, may drift from the source.
# Source: packages/agent_runtime/crescendo_agent/vision_loop.py (9130a21, Nov 13 2026).
# Called by file 1. Uses file 3 (model), file 4 (authorize), file 5 (desktop).

"""Bounded screenshot -> proposal -> gateway -> scroll/finish execution."""
# ^ One-line summary: look, let the model propose, check permission, then act.

import json  # Used to write the model's proposal into the history as JSON text.
import math  # Used for math.isfinite, to reject NaN/infinite deadlines.
import time  # Provides time.monotonic, a clock that never jumps backwards.

from crescendo_security.policy import Decision, authorize  # authorize() = the permission check; Decision = its yes/no + reason.

from .loop import AgentState, RunResult  # Shared with the text agent: run state and the final result type.
from .model import Entry  # One history line: a kind ("goal", "observation", "action", "denied") plus text.
from .vision import valid_finish  # Checks a finish answer is a nonblank string of at most 2000 characters.


def run_vision_agent(goal, grant, desktop, model, *, max_steps=5,  # Inputs: goal text, permissions, desktop, model; at most 5 steps by default.
                     deadline_seconds=120.0, clock=time.monotonic,  # Time limit; `clock` is replaceable so tests can fake time.
                     on_screenshot=None, finish_validator=None) -> RunResult:  # Optional hooks: save images; extra answer check.
    if type(max_steps) is not int or not 1 <= max_steps <= 10:  # Refuse silly limits (e.g. 0, 1000, 2.5, True).
        raise ValueError("max_steps must be an integer from 1 to 10.")  # Fail before spending anything.
    if not math.isfinite(deadline_seconds) or not 0 < deadline_seconds <= 120:  # Refuse NaN, infinity, 0, or > 2 minutes.
        raise ValueError("deadline_seconds must be positive and at most 120.")  # Same: fail early.
    state = AgentState(goal, grant)  # Fresh run state: empty history and empty denied list.
    state.transcript.append(Entry("goal", goal))  # First history line: the goal. The model sees it every step.
    deadline = clock() + deadline_seconds  # Absolute time after which we stop.
    for step in range(max_steps):  # Repeat at most max_steps times (step = 0, 1, 2, ...).
        if clock() >= deadline:  # Out of time before even looking?
            return state.stop("deadline")  # End the run with status "deadline".
        screenshot = desktop.capture_screen()  # Take a fresh picture of the whole desktop (permission-checked inside).
        if on_screenshot is not None:  # If the caller wants copies...
            on_screenshot(step + 1, screenshot)  # ...hand over this exact image (numbered from 1). Saved before the model sees it.
        state.transcript.append(Entry("observation", f"Current screenshot captured: {screenshot.size}. Image supplied separately."))  # Note it in history; the image itself is NOT stored in the history.
        if clock() >= deadline:  # Did capturing take us past the deadline?
            return state.stop("deadline")  # Then don't spend a model call.
        call = model.decide(screenshot, state.transcript)  # Ask the model: "given this image and history, pick ONE action."
        state.transcript.append(Entry("action", json.dumps({"tool": call.name, "args": dict(call.args)})))  # Record what it proposed (even if we later deny it).
        # A model request already in flight can overrun; admit no action afterward.
        if clock() >= deadline:  # Did the model call push us past the deadline?
            return state.stop("deadline")  # Then do NOT carry out the late proposal.
        decision = authorize(grant, call)  # Permission check: is this tool granted and are its arguments valid? (file 4)
        if decision.allowed and call.name not in {"scroll", "finish"}:  # Allowed by the grant but not something THIS loop can do?
            decision = Decision(False, "This vision loop supports only scroll and finish.")  # Turn it into a denial.
        if decision.allowed and call.name == "finish" and not valid_finish(dict(call.args)):  # Finishing with a blank or huge answer?
            decision = Decision(False, "finish requires one nonblank answer of at most 2000 characters.")  # Deny it.
        if decision.allowed and call.name == "finish" and finish_validator is not None:  # Caller supplied an extra answer check?
            reason = finish_validator(call.args["answer"])  # Run it (in the demo: "is it 6 hex characters?").
            if reason is not None:  # It returned a complaint...
                decision = Decision(False, reason)  # ...so deny, using that complaint as the reason.
        if not decision.allowed:  # Any check said no?
            state.denied.append((call, decision))  # Remember the rejected proposal for the final report.
            state.transcript.append(Entry("denied", decision.reason))  # Tell the model why, so its next step can adjust.
            continue  # Skip the action; go to the next step (which takes a new screenshot).
        if call.name == "finish":  # Allowed finish?
            return state.stop("finished", call.args["answer"])  # Done: return the answer.
        desktop.scroll(call.args["direction"], call.args["amount"])  # Otherwise it's an allowed scroll: do it (re-checked inside, file 5).
        state.transcript.append(Entry("observation", "Authorized scroll completed. Inspect the next screenshot for its effect."))  # The SDK returning doesn't prove the page moved; the next image is the evidence.
    return state.stop("step_limit")  # Used every step without finishing: stop with status "step_limit".
