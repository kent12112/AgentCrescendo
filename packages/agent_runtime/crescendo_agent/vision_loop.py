# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Bounded screenshot -> proposal -> gateway -> scroll/finish execution."""
# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: Import math: checks numeric validity, including NaN and infinity.
import math
# Learn: Import time: measures monotonic elapsed time and provides bounded pauses.
import time

# Learn: From crescendo_security.policy, import Decision (holds an allow/deny result and a safe
# explanation); authorize (checks task grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import Decision, authorize

# Learn: From .loop, import AgentState (collects mutable state for one bounded agent run); RunResult
# (captures the final state, answer, sources, transcript and denials).
from .loop import AgentState, RunResult
# Learn: From .model, import Entry (represents one typed transcript item sent to the model).
from .model import Entry
# Learn: From .vision, import Proposal (pairs the proposed action with an untrusted display reason);
# RateLimited (carries only a retry delay, without leaking provider error text); downscale (shrinks the PNG
# before both saving and model submission); valid_finish (checks that finish has exactly one bounded
# nonblank answer).
from .vision import Proposal, RateLimited, downscale, valid_finish

# Longest provider-requested pause we accept before one retry within a step.
# Learn: Set MAX_RATE_LIMIT_WAIT to 15.0.
MAX_RATE_LIMIT_WAIT = 15.0


# Learn: Define run_vision_agent(goal, grant, desktop, model, max_steps, deadline_seconds, clock, sleep,
# on_screenshot, finish_validator, max_image_width, on_rate_limit). The body runs when called, not when
# defined.
def run_vision_agent(goal, grant, desktop, model, *, max_steps=5,
                     # Learn: Parameters: deadline_seconds is provided/defaulted by the caller (the
                     # host-enforced duration limit; it does not interrupt an in-flight SDK call); clock is
                     # provided/defaulted by the caller (an injectable clock so tests can advance time
                     # without sleeping); sleep is provided/defaulted by the caller. Type hints do not
                     # enforce types by themselves.
                     deadline_seconds=120.0, clock=time.monotonic, sleep=time.sleep,
                     # Learn: Parameters: on_screenshot is provided/defaulted by the caller;
                     # finish_validator is provided/defaulted by the caller. Type hints do not enforce types
                     # by themselves.
                     on_screenshot=None, finish_validator=None,
                     # Learn: Parameters: max_image_width is provided/defaulted by the caller (the optional
                     # width cap applied before saving and sending screenshots); on_rate_limit is
                     # provided/defaulted by the caller. Type hints do not enforce types by themselves.
                     max_image_width=None, on_rate_limit=None) -> RunResult:
    # Learn: Take this branch only if the exact Python type of max_steps is not int OR not (1 is at most
    # max_steps is at most 10).
    if type(max_steps) is not int or not 1 <= max_steps <= 10:
        # Learn: Raise ValueError('max_steps must be an integer from 1 to 10.') to stop the normal path.
        raise ValueError("max_steps must be an integer from 1 to 10.")
    # Learn: Take this branch only if not (math.isfinite(deadline_seconds)) OR not (0 is less than
    # deadline_seconds is at most 120).
    if not math.isfinite(deadline_seconds) or not 0 < deadline_seconds <= 120:
        # Learn: Raise ValueError('deadline_seconds must be positive and at most 120.') to stop the normal
        # path.
        raise ValueError("deadline_seconds must be positive and at most 120.")
    # Learn: Set state to AgentState(goal, grant); the current run goal, permissions, transcript, and denied
    # proposals.
    state = AgentState(goal, grant)
    # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('goal', goal).
    state.transcript.append(Entry("goal", goal))
    # Learn: Set deadline to clock() plus deadline_seconds; the absolute monotonic-clock cutoff for
    # admitting further work.
    deadline = clock() + deadline_seconds
    # Learn: Iterate over range(max_steps), binding step for each item.
    for step in range(max_steps):
        # Learn: Take this branch only if clock() is at least deadline.
        if clock() >= deadline:
            # Learn: Return state.stop('deadline') to the caller and stop this function.
            return state.stop("deadline")
        # Learn: Set screenshot to desktop.capture_screen(); the current PNG observation supplied to the
        # vision model. Capture a fresh whole-desktop PNG through the permission-checked adapter.
        screenshot = desktop.capture_screen()
        # Learn: Take this branch only if max_image_width is not None (no value).
        if max_image_width is not None:
            # Scale before saving so the saved PNG stays exactly what the model receives.
            # Learn: Set screenshot to downscale(screenshot, max_image_width); the current PNG observation
            # supplied to the vision model. Reduce image width while preserving aspect ratio before
            # saving/model input.
            screenshot = downscale(screenshot, max_image_width)
        # Learn: Take this branch only if on_screenshot is not None (no value).
        if on_screenshot is not None:
            # Learn: Call on_screenshot with the arguments shown.
            on_screenshot(step + 1, screenshot)
        # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('observation',
        # f'Current screenshot captured: {screenshot.size}. Image supplied separately.').
        state.transcript.append(Entry("observation", f"Current screenshot captured: {screenshot.size}. Image supplied separately."))
        # Learn: Take this branch only if clock() is at least deadline.
        if clock() >= deadline:
            # Learn: Return state.stop('deadline') to the caller and stop this function.
            return state.stop("deadline")
        # Learn: Try the following operations; matching except clauses handle failures.
        try:
            # Learn: Set proposal to model.decide(screenshot, state.transcript); the model action plus its
            # optional, untrusted display reason. Ask the adapter for a proposal; this does not itself
            # execute a tool.
            proposal = model.decide(screenshot, state.transcript)
        # Learn: Handle RateLimited as limited; unmatched errors propagate.
        except RateLimited as limited:
            # One bounded wait per step, only if it fits before the deadline. No
            # transcript entry: provider throttling is not page evidence.
            # Learn: Set wait to limited.retry_after; the provider-requested retry delay, checked against
            # local limits.
            wait = limited.retry_after
            # Learn: Take this branch only if wait is greater than MAX_RATE_LIMIT_WAIT OR clock() plus wait
            # is at least deadline.
            if wait > MAX_RATE_LIMIT_WAIT or clock() + wait >= deadline:
                # Learn: Return state.stop('rate_limited') to the caller and stop this function.
                return state.stop("rate_limited")
            # Learn: Take this branch only if on_rate_limit is not None (no value).
            if on_rate_limit is not None:
                # Learn: Call on_rate_limit with the arguments shown.
                on_rate_limit(step + 1, wait)
            # Learn: Pause for the requested duration; callers must bound this wait; inputs: wait.
            sleep(wait)
            # Learn: Try the following operations; matching except clauses handle failures.
            try:
                # Learn: Set proposal to model.decide(screenshot, state.transcript); the model action plus
                # its optional, untrusted display reason. Ask the adapter for a proposal; this does not
                # itself execute a tool.
                proposal = model.decide(screenshot, state.transcript)
            # Learn: Handle RateLimited; unmatched errors propagate.
            except RateLimited:
                # Learn: Return state.stop('rate_limited') to the caller and stop this function.
                return state.stop("rate_limited")
        # Models may return a bare ToolCall (no reason) or a Proposal.
        # Learn: Set (call, reason) to the tuple (proposal.call, proposal.reason) (positional values) when
        # proposal has type Proposal (including subclasses), otherwise the tuple (proposal, None)
        # (positional values).
        call, reason = (proposal.call, proposal.reason) if isinstance(proposal, Proposal) else (proposal, None)
        # Learn: Set action to a new dictionary with keys 'tool', 'args'.
        action = {"tool": call.name, "args": dict(call.args)}
        # Learn: Take this branch only if reason is not None (no value).
        if reason is not None:
            # Learn: Set action['reason'] to reason.
            action["reason"] = reason  # The model's own, untrusted account; display only.
        # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('action',
        # json.dumps(action)).
        state.transcript.append(Entry("action", json.dumps(action)))
        # A model request already in flight can overrun; admit no action afterward.
        # Learn: Take this branch only if clock() is at least deadline.
        if clock() >= deadline:
            # Learn: Return state.stop('deadline') to the caller and stop this function.
            return state.stop("deadline")
        # Learn: Set decision to authorize(grant, call); the gateway allow/deny result and its explanation.
        # Check the proposed action against the fixed task grant before any effect.
        decision = authorize(grant, call)
        # Learn: Take this branch only if decision.allowed AND call.name is not in a set of 'scroll',
        # 'finish' (unique members).
        if decision.allowed and call.name not in {"scroll", "finish"}:
            # Learn: Set decision to Decision(False, 'This vision loop supports only scroll and finish.');
            # the gateway allow/deny result and its explanation.
            decision = Decision(False, "This vision loop supports only scroll and finish.")
        # Learn: Take this branch only if decision.allowed AND call.name equals 'finish' AND not
        # (valid_finish(dict(call.args))).
        if decision.allowed and call.name == "finish" and not valid_finish(dict(call.args)):
            # Learn: Set decision to Decision(False, 'finish requires one nonblank answer of at most 2000
            # characters.'); the gateway allow/deny result and its explanation.
            decision = Decision(False, "finish requires one nonblank answer of at most 2000 characters.")
        # Learn: Take this branch only if decision.allowed AND call.name equals 'finish' AND
        # finish_validator is not None (no value).
        if decision.allowed and call.name == "finish" and finish_validator is not None:
            # Learn: Set reason to finish_validator(call.args['answer']); the explanatory text; a model
            # reason is display data, not authority.
            reason = finish_validator(call.args["answer"])
            # Learn: Take this branch only if reason is not None (no value).
            if reason is not None:
                # Learn: Set decision to Decision(False, reason); the gateway allow/deny result and its
                # explanation.
                decision = Decision(False, reason)
        # Learn: Take this branch only if not (decision.allowed).
        if not decision.allowed:
            # Learn: Append one item to the ordered collection on state.denied; inputs: the tuple (call,
            # decision) (positional values).
            state.denied.append((call, decision))
            # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('denied',
            # decision.reason).
            state.transcript.append(Entry("denied", decision.reason))
            # Learn: Skip the rest of this iteration and retry from the next loop iteration.
            continue
        # Learn: Take this branch only if call.name equals 'finish'.
        if call.name == "finish":
            # Learn: Return state.stop('finished', call.args['answer']) to the caller and stop this
            # function.
            return state.stop("finished", call.args["answer"])
        # Learn: Execute the already-checked wheel action; the next screenshot shows its effect on desktop;
        # inputs: call.args['direction'], call.args['amount'].
        desktop.scroll(call.args["direction"], call.args["amount"])
        # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('observation',
        # 'Authorized scroll completed. Inspect the next screenshot for its effect.').
        state.transcript.append(Entry("observation", "Authorized scroll completed. Inspect the next screenshot for its effect."))
    # Learn: Return state.stop('step_limit') to the caller and stop this function.
    return state.stop("step_limit")
