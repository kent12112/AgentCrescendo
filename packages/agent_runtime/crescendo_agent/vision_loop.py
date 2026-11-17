"""Bounded screenshot -> proposal -> gateway -> scroll/finish execution."""
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import math: checks numeric validity, including NaN and infinity.
import math
# Import time: measures monotonic elapsed time and provides bounded pauses.
import time

# Import from crescendo_security.policy: Decision (holds an allow/deny result and a safe
# explanation); authorize (checks task grants and argument bounds before a proposed tool can
# execute).
from crescendo_security.policy import Decision, ToolCall, authorize

# Import from .loop: AgentState (collects mutable state for one bounded agent run); RunResult
# (captures the final state, answer, sources, transcript and denials).
from .loop import AgentState, RunResult
# Import from .model: Entry (represents one typed transcript item sent to the model).
from .desktop import ActionDenied
from .model import Entry
# Import from .vision: Proposal (pairs the proposed action with an untrusted display reason);
# RateLimited (carries only a retry delay, without leaking provider error text); downscale (shrinks
# the PNG before both saving and model submission); valid_finish (checks that finish has exactly one
# bounded nonblank answer).
from .vision import (GRID_NOTE, ModelTimedOut, ModelUnavailable, Proposal, RateLimited,
                     add_grid, downscale, valid_finish)

# Longest provider-requested pause we accept before one retry within a step.
# Set MAX_RATE_LIMIT_WAIT to 15.0.
MAX_RATE_LIMIT_WAIT = 15.0


# Define run_vision_agent with parameters goal, grant, desktop, model, max_steps, deadline_seconds,
# clock, sleep, on_screenshot, finish_validator, max_image_width, on_rate_limit.
def run_vision_agent(goal, grant, desktop, model, *, max_steps=5,
                     deadline_seconds=120.0, clock=time.monotonic, sleep=time.sleep,
                     on_screenshot=None, finish_validator=None,
                     max_image_width=None, on_rate_limit=None, grid=False,
                     link_grounding=False,
                     max_rate_limit_wait=MAX_RATE_LIMIT_WAIT,
                     on_model_timeout=None, on_model_unavailable=None) -> RunResult:
    # Check whether the exact type of max_steps is not int or not (1 is at most max_steps and is at
    # most 10).
    if type(max_steps) is not int or not 1 <= max_steps <= 10:
        # Raise ValueError('max_steps must be an integer from 1 to 10.') to stop the normal path.
        raise ValueError("max_steps must be an integer from 1 to 10.")
    # Check whether not (math.isfinite(deadline_seconds)) or not (0 is less than deadline_seconds
    # and is at most 120).
    if not math.isfinite(deadline_seconds) or not 0 < deadline_seconds <= 120:
        # Raise ValueError('deadline_seconds must be positive and at most 120.') to stop the normal
        # path.
        raise ValueError("deadline_seconds must be positive and at most 120.")
    if not math.isfinite(max_rate_limit_wait) or not 0 <= max_rate_limit_wait <= 60:
        raise ValueError("max_rate_limit_wait must be between 0 and 60 seconds.")
    # Set state to AgentState(goal, grant).
    state = AgentState(goal, grant)
    # Append Entry('goal', goal) to state.transcript.
    state.transcript.append(Entry("goal", goal))
    # Set deadline to clock() plus deadline_seconds.
    deadline = clock() + deadline_seconds
    # Iterate over range(max_steps), binding step for each item.
    for step in range(max_steps):
        # Check whether clock() is at least deadline.
        if clock() >= deadline:
            # Return state.stop('deadline').
            return state.stop("deadline")
        # Set screenshot to desktop.capture_screen().
        screenshot = desktop.capture_screen()
        # Real screen size, before any downscaling: click coordinates are converted to it.
        screen_size = screenshot.size
        # DOM assistance is opt-in. The model gets labels/IDs, never URLs or selectors.
        targets = desktop.visible_links() if link_grounding and "click" in grant.allowed_tools else []
        # Check whether max_image_width is not None.
        if max_image_width is not None:
            # Scale before saving so the saved PNG stays exactly what the model receives.
            # Set screenshot to downscale(screenshot, max_image_width).
            screenshot = downscale(screenshot, max_image_width)
        if grid:
            # After scaling, so labels stay readable and match the image the model gets.
            screenshot = add_grid(screenshot)
        # Check whether on_screenshot is not None.
        if on_screenshot is not None:
            # Call on_screenshot with step plus 1, screenshot.
            on_screenshot(step + 1, screenshot)
        # Append Entry('observation', f'Current screenshot captured: {screenshot.size}. Image
        # supplied separately.') to state.transcript.
        note = " " + GRID_NOTE if grid else ""
        state.transcript.append(Entry("observation", f"Current screenshot captured: {screenshot.size}. Image supplied separately.{note}"))
        if link_grounding:
            state.transcript.append(Entry("visible_links", json.dumps(targets)))
        # Check whether clock() is at least deadline.
        if clock() >= deadline:
            # Return state.stop('deadline').
            return state.stop("deadline")
        # At most two inference requests per step, shared across transient errors.
        # No desktop action has run for either request until a proposal is returned.
        failures = []
        for attempt in range(2):
            if clock() >= deadline:
                state.transcript.extend(failures)
                return state.stop("deadline")
            try:
                proposal = model.decide(screenshot, state.transcript)
            except (RateLimited, ModelTimedOut, ModelUnavailable) as failure:
                timed_out = isinstance(failure, ModelTimedOut)
                unavailable = isinstance(failure, ModelUnavailable)
                failure_status = ("model_timeout" if timed_out else
                                  "model_unavailable" if unavailable else "rate_limited")
                if timed_out:
                    failures.append(Entry("model_error", "Model request timed out; no proposal received."))
                if unavailable:
                    failures.append(Entry("model_error", "Model service unavailable; no proposal received."))
                if clock() >= deadline:
                    state.transcript.extend(failures)
                    return state.stop("deadline")
                if attempt == 1:
                    state.transcript.extend(failures)
                    return state.stop(failure_status)
                if timed_out:
                    if on_model_timeout is not None:
                        on_model_timeout(step + 1)
                    continue
                wait = failure.retry_after
                if wait > max_rate_limit_wait or clock() + wait >= deadline:
                    state.transcript.extend(failures)
                    return state.stop(failure_status)
                if unavailable and on_model_unavailable is not None:
                    on_model_unavailable(step + 1, wait)
                if not unavailable and on_rate_limit is not None:
                    on_rate_limit(step + 1, wait)
                sleep(wait)
            else:
                # Record provider failures after retrying so the retry input is identical.
                state.transcript.extend(failures)
                break
        # Models may return a bare ToolCall (no reason) or a Proposal.
        # Set (call, reason) to (proposal.call, proposal.reason) if whether proposal is an instance
        # of Proposal, otherwise (proposal, None).
        call, reason = (proposal.call, proposal.reason) if isinstance(proposal, Proposal) else (proposal, None)
        # Set action to {'tool': call.name, 'args': dict(call.args)}.
        action = {"tool": call.name, "args": dict(call.args)}
        # Click preparation only for granted clicks; authorize() denies the rest unchanged.
        clicking = call.name in {"click", "click_link"} and "click" in grant.allowed_tools
        coordinate_problem = None
        if clicking:
            try:
                if call.name == "click_link":
                    if not link_grounding:
                        raise ActionDenied("Visible-link selection is not enabled.")
                    if set(call.args) != {"target_id"} or type(call.args.get("target_id")) is not int:
                        raise ActionDenied("click_link requires one integer target_id from the current observation.")
                    x, y = desktop.resolve_link(call.args["target_id"])
                    call = ToolCall("click", {"x": x, "y": y})
                    action["resolved_tool"] = "click"
                else:
                    call = to_screen(call, screenshot.size, screen_size)
            except ActionDenied as denied:
                coordinate_problem = str(denied)
            if call.args != action["args"]:
                # Record both: what the model proposed and the screen pixel it maps to.
                action["screen"] = dict(call.args)
        # Check whether reason is not None.
        if reason is not None:
            # Set action['reason'] to reason.
            action["reason"] = reason  # The model's own, untrusted account; display only.
        # Append Entry('action', json.dumps(action)) to state.transcript.
        state.transcript.append(Entry("action", json.dumps(action)))
        # A model request already in flight can overrun; admit no action afterward.
        # Check whether clock() is at least deadline.
        if clock() >= deadline:
            # Return state.stop('deadline').
            return state.stop("deadline")
        # Set decision to authorize(grant, call).
        # Only clicks need the page area; asking for it costs a browser round trip.
        area = desktop.click_area() if clicking and coordinate_problem is None else None
        decision = (Decision(False, coordinate_problem) if coordinate_problem is not None
                    else authorize(grant, call, click_area=area))
        if decision.allowed and call.name not in {"scroll", "finish", "click"}:
            decision = Decision(False, "This vision loop supports only scroll, click, and finish.")
        # Check whether decision.allowed and call.name equals 'finish' and not
        # (valid_finish(dict(call.args))).
        if decision.allowed and call.name == "finish" and not valid_finish(dict(call.args)):
            # Set decision to Decision(False, 'finish requires one nonblank answer of at most 2000
            # characters.').
            decision = Decision(False, "finish requires one nonblank answer of at most 2000 characters.")
        # Check whether decision.allowed and call.name equals 'finish' and finish_validator is not
        # None.
        if decision.allowed and call.name == "finish" and finish_validator is not None:
            # Set reason to finish_validator(call.args['answer']).
            reason = finish_validator(call.args["answer"])
            # Check whether reason is not None.
            if reason is not None:
                # Set decision to Decision(False, reason).
                decision = Decision(False, reason)
        # Check whether not (decision.allowed).
        if not decision.allowed:
            # Append (call, decision) to state.denied.
            state.denied.append((call, decision))
            # Append Entry('denied', decision.reason) to state.transcript.
            state.transcript.append(Entry("denied", decision.reason))
            # Skip this item and continue with the next iteration.
            continue
        # Check whether call.name equals 'finish'.
        if call.name == "finish":
            # Return state.stop('finished', call.args['answer']).
            return state.stop("finished", call.args["answer"])
        if call.name == "click":
            try:
                # The desktop checks what is under the point before pressing the button.
                outcome = desktop.click(call.args["x"], call.args["y"])
            except ActionDenied as denied:
                decision = Decision(False, str(denied))
                state.denied.append((call, decision))
                state.transcript.append(Entry("denied", decision.reason))
                continue
            state.transcript.append(Entry("observation", "Authorized click completed. " + outcome))
            continue
        # Call desktop.scroll with call.args['direction'], call.args['amount'].
        desktop.scroll(call.args["direction"], call.args["amount"])
        # Append Entry('observation', 'Authorized scroll completed. Inspect the next screenshot for
        # its effect.') to state.transcript.
        state.transcript.append(Entry("observation", "Authorized scroll completed. Inspect the next screenshot for its effect."))
    # Return state.stop('step_limit').
    return state.stop("step_limit")


def to_screen(call: ToolCall, image_size, screen_size) -> ToolCall:
    """Convert a click from the image the model saw to real screen pixels.

    The model may see a downscaled screenshot (max_image_width), so (x, y) in that
    image must be scaled back up. Malformed arguments pass through unchanged for
    the gateway to deny.
    """
    x, y = call.args.get("x"), call.args.get("y")
    if set(call.args) != {"x", "y"} or type(x) is not int or type(y) is not int:
        return call
    (image_w, image_h), (screen_w, screen_h) = image_size, screen_size
    return ToolCall("click", {"x": round(x * screen_w / image_w), "y": round(y * screen_h / image_h)})
