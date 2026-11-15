# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""The bounded observe -> decide -> authorize -> act loop for one agent."""
# Learn: Import time: measures monotonic elapsed time and provides bounded pauses.
import time
# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: From collections.abc, import Callable (describes a function-valued input such as an injected
# clock).
from collections.abc import Callable
# Learn: From dataclasses, import dataclass (generates data-container initialization and comparison
# methods); field (configures a dataclass field, including per-instance factories and repr hiding).
from dataclasses import dataclass, field
# Learn: From typing, import Literal (restricts a type annotation to explicit known values).
from typing import Literal

# Learn: From crescendo_security.policy, import Decision (holds an allow/deny result and a safe
# explanation); TaskGrant (holds the task identity and immutable tool/host allowlists); ToolCall (holds an
# untrusted proposed tool name and argument mapping); authorize (checks task grants and argument bounds
# before a proposed tool can execute).
from crescendo_security.policy import Decision, TaskGrant, ToolCall, authorize

# Learn: From .desktop, import Desktop (the structural text-browser interface used by the loop); Observation
# (holds current page URL, bounded text, and observed links).
from .desktop import Desktop, Observation
# Learn: From .model, import TOOLS (the text-loop tool schemas offered to the model); Entry (represents one
# typed transcript item sent to the model); Model (the provider-neutral structural decision interface).
from .model import TOOLS, Entry, Model


# Learn: Decorate the class with generated data-container methods.
@dataclass
# Learn: Define RunResult. Indented methods and attributes belong to this class.
class RunResult:
    # Learn: Declare status with type Literal['finished', 'step_limit', 'deadline', 'rate_limited']; the
    # draft or agent termination state returned to the caller.
    status: Literal["finished", "step_limit", "deadline", "rate_limited"]
    # Learn: Declare answer with type str | None; the final answer text; a returned string alone does not
    # prove correctness.
    answer: str | None
    # Learn: Declare sources with type list[str]; the source URLs reported with the answer.
    sources: list[str]
    # Learn: Declare transcript with type list[Entry]; the ordered goal, observation, proposal, and denial
    # history.
    transcript: list[Entry]
    # Learn: Declare denied with type list[tuple[ToolCall, Decision]]; the rejected proposals retained for
    # diagnosis.
    denied: list[tuple[ToolCall, Decision]]


# Learn: Decorate the class with generated data-container methods.
@dataclass
# Learn: Define AgentState. Indented methods and attributes belong to this class.
class AgentState:
    # Learn: Declare goal with type str; the user task text.
    goal: str
    # Learn: Declare grant with type TaskGrant; the task identity and fixed tool/host permissions; model
    # output cannot expand these.
    grant: TaskGrant
    # Learn: Set transcript to field(default_factory=list); the ordered goal, observation, proposal, and
    # denial history. Configure a per-instance default or representation option for this dataclass field.
    transcript: list[Entry] = field(default_factory=list)
    # Learn: Set denied to field(default_factory=list); the rejected proposals retained for diagnosis.
    # Configure a per-instance default or representation option for this dataclass field.
    denied: list[tuple[ToolCall, Decision]] = field(default_factory=list)
    # Learn: Set pending_observation to None (no value); a search result to consume instead of another
    # full-page preview.
    pending_observation: Observation | None = None

    # Learn: Define stop(status, answer, sources). The body runs when called, not when defined.
    def stop(self, status, answer=None, sources=()) -> RunResult:
        # Learn: Return RunResult(status, answer, list(sources), self.transcript, self.denied) to the caller
        # and stop this function.
        return RunResult(status, answer, list(sources), self.transcript, self.denied)


# Learn: Define step(state, desktop, model). The body runs when called, not when defined.
def step(state: AgentState, desktop: Desktop, model: Model) -> RunResult | None:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: One observe -> decide ->
    # authorize -> act cycle.. It remains unchanged at runtime.
    # Learn string line 3: Literal prompt, documentation, or fixture content: Return a RunResult when the
    # agent finishes; return None to keep looping.. It remains unchanged at runtime.
    # Learn string line 5: Literal prompt, documentation, or fixture content: 1. Observe: obs =
    # desktop.observe(). Append Entry("observation", ...) holding. It remains unchanged at runtime.
    # Learn string line 6: Literal prompt, documentation, or fixture content: the URL and page text, so the
    # model can see where it is and what it read.. It remains unchanged at runtime.
    # Learn string line 7: Literal prompt, documentation, or fixture content: 2. Decide: call =
    # model.decide(state.transcript, TOOLS).. It remains unchanged at runtime.
    # Learn string line 8: Literal prompt, documentation, or fixture content: Append Entry("action", ...)
    # describing the call.. It remains unchanged at runtime.
    # Learn string line 9: Literal prompt, documentation, or fixture content: 3. Authorize: decision =
    # authorize(state.grant, call). If denied, append. It remains unchanged at runtime.
    # Learn string line 10: Literal prompt, documentation, or fixture content: Entry("denied",
    # decision.reason), record (call, decision) in state.denied,. It remains unchanged at runtime.
    # Learn string line 11: Literal prompt, documentation, or fixture content: and return None. Do NOT
    # perform the action. The model will see the denial. It remains unchanged at runtime.
    # Learn string line 12: Literal prompt, documentation, or fixture content: on its next decision and can
    # choose something else.. It remains unchanged at runtime.
    # Learn string line 13: Literal prompt, documentation, or fixture content: 4. Act:. It remains unchanged
    # at runtime.
    # Learn string line 14: Literal prompt, documentation, or fixture content: - "navigate":
    # desktop.navigate(call.args["url"]); return None.. It remains unchanged at runtime.
    # Learn string line 15: Literal prompt, documentation, or fixture content: - "search_page": save a
    # bounded search observation for the next step;. It remains unchanged at runtime.
    # Learn string line 16: Literal prompt, documentation, or fixture content: do not append another
    # full-page preview on that step.. It remains unchanged at runtime.
    # Learn string line 17: Literal prompt, documentation, or fixture content: - "finish": return
    # state.stop("finished", call.args["answer"], call.args["sources"]).. It remains unchanged at runtime.
    # Learn string line 18: Literal prompt, documentation, or fixture content: - any other name: raise
    # ValueError. A tool that was granted but has no. It remains unchanged at runtime.
    # Learn string line 19: Literal prompt, documentation, or fixture content: implementation is a
    # configuration bug, not something to skip silently.. It remains unchanged at runtime.
    # Learn string line 21: Literal prompt, documentation, or fixture content: Think about: which entries
    # contain untrusted text, and what would happen if. It remains unchanged at runtime.
    # Learn string line 22: Literal prompt, documentation, or fixture content: step 3 came after step 4.. It
    # remains unchanged at runtime.
    """One observe -> decide -> authorize -> act cycle.

    Return a RunResult when the agent finishes; return None to keep looping.

    1. Observe: obs = desktop.observe(). Append Entry("observation", ...) holding
       the URL and page text, so the model can see where it is and what it read.
    2. Decide: call = model.decide(state.transcript, TOOLS).
       Append Entry("action", ...) describing the call.
    3. Authorize: decision = authorize(state.grant, call). If denied, append
       Entry("denied", decision.reason), record (call, decision) in state.denied,
       and return None. Do NOT perform the action. The model will see the denial
       on its next decision and can choose something else.
    4. Act:
       - "navigate": desktop.navigate(call.args["url"]); return None.
       - "search_page": save a bounded search observation for the next step;
         do not append another full-page preview on that step.
       - "finish": return state.stop("finished", call.args["answer"], call.args["sources"]).
       - any other name: raise ValueError. A tool that was granted but has no
         implementation is a configuration bug, not something to skip silently.

    Think about: which entries contain untrusted text, and what would happen if
    step 3 came after step 4.
    """
    # 1. Observe. Page text is untrusted: it may contain instructions aimed at the model.
    # Learn: Set obs to state.pending_observation when state.pending_observation is not None (no value),
    # otherwise desktop.observe().
    obs = state.pending_observation if state.pending_observation is not None else desktop.observe()
    # Learn: Set state.pending_observation to None (no value); a search result to consume instead of another
    # full-page preview.
    state.pending_observation = None
    # Learn: Set observation to an f-string that substitutes the expressions in {...} into the text.
    observation = f"URL: {obs.url}\n{obs.text}"
    # Learn: Take this branch only if obs.links.
    if obs.links:
        # Learn: Update observation using its previous value plus '\nPage links (untrusted): ' plus
        # json.dumps([{'label': link.label, 'url': link.url} for link in obs.links]).
        observation += "\nPage links (untrusted): " + json.dumps([
            # Learn: Supply the next argument to json.dumps: {"label": link.label, "url": link.url} for link
            # in obs.links.
            {"label": link.label, "url": link.url} for link in obs.links
        # Learn: Close the argument list for json.dumps; the grouped expression remains one call.
        ])
    # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('observation',
    # observation).
    state.transcript.append(Entry("observation", observation))

    # 2. Decide. The model only proposes; it has no ability to act on its own.
    # Learn: Set call to model.decide(state.transcript, TOOLS); the proposed tool name and arguments, still
    # untrusted until authorized. Ask the adapter for a proposal; this does not itself execute a tool.
    call = model.decide(state.transcript, TOOLS)
    # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('action',
    # f'{call.name} {dict(call.args)}').
    state.transcript.append(Entry("action", f"{call.name} {dict(call.args)}"))

    # 3. Authorize BEFORE acting. If this came after step 4, a denied action
    # would already have happened and the check would only be a log entry.
    # Learn: Set decision to authorize(state.grant, call); the gateway allow/deny result and its
    # explanation. Check the proposed action against the fixed task grant before any effect.
    decision = authorize(state.grant, call)
    # Learn: Take this branch only if not (decision.allowed).
    if not decision.allowed:
        # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('denied',
        # decision.reason).
        state.transcript.append(Entry("denied", decision.reason))
        # Learn: Append one item to the ordered collection on state.denied; inputs: the tuple (call,
        # decision) (positional values).
        state.denied.append((call, decision))
        # Learn: Return None (no value) to the caller and stop this function.
        return None

    # 4. Act.
    # Learn: Take this branch only if call.name equals 'navigate'.
    if call.name == "navigate":
        # Learn: Open the requested destination through the desktop adapter on desktop; inputs:
        # call.args['url'].
        desktop.navigate(call.args["url"])
        # Learn: Return None (no value) to the caller and stop this function.
        return None
    # Learn: Take this branch only if call.name equals 'search_page'.
    if call.name == "search_page":
        # Learn: Set state.pending_observation to desktop.search_page(call.args['query']); a search result
        # to consume instead of another full-page preview. Search current-page text without navigating to
        # another URL.
        state.pending_observation = desktop.search_page(call.args["query"])
        # Learn: Return None (no value) to the caller and stop this function.
        return None
    # Learn: Take this branch only if call.name equals 'finish'.
    if call.name == "finish":
        # Learn: Return state.stop('finished', call.args['answer'], call.args['sources']) to the caller and
        # stop this function.
        return state.stop("finished", call.args["answer"], call.args["sources"])
    # Learn: Raise ValueError(f"Tool '{call.name}' is granted but has no implementation.") to stop the
    # normal path.
    raise ValueError(f"Tool '{call.name}' is granted but has no implementation.")


# Learn: Define run_agent(goal, grant, desktop, model, max_steps, deadline_seconds, clock). The body runs
# when called, not when defined.
def run_agent(
    # Learn: Parameters: goal has type str (the user task text). Type hints do not enforce types by
    # themselves.
    goal: str,
    # Learn: Parameters: grant has type TaskGrant (the task identity and fixed tool/host permissions; model
    # output cannot expand these). Type hints do not enforce types by themselves.
    grant: TaskGrant,
    # Learn: Parameters: desktop has type Desktop. Type hints do not enforce types by themselves.
    desktop: Desktop,
    # Learn: Parameters: model has type Model (the provider adapter or scripted test model used to propose
    # actions). Type hints do not enforce types by themselves.
    model: Model,
    # Learn: Parameters after * must be passed by keyword, which makes optional controls explicit.
    *,
    # Learn: Parameters: max_steps has type int (the maximum loop iterations, enforced outside the model).
    # Type hints do not enforce types by themselves.
    max_steps: int = 10,
    # Learn: Parameters: deadline_seconds has type float (the host-enforced duration limit; it does not
    # interrupt an in-flight SDK call). Type hints do not enforce types by themselves.
    deadline_seconds: float = 120.0,
    # Learn: Parameters: clock has type Callable[[], float] (an injectable clock so tests can advance time
    # without sleeping). Type hints do not enforce types by themselves.
    clock: Callable[[], float] = time.monotonic,
# Learn: Finish the function signature; -> declares the return type and the following indented lines form
# the function body.
) -> RunResult:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: Run step() until the agent
    # finishes or a limit stops it.. It remains unchanged at runtime.
    # Learn string line 3: Literal prompt, documentation, or fixture content: Limits live here, outside the
    # model: a model that never calls finish, loops,. It remains unchanged at runtime.
    # Learn string line 4: Literal prompt, documentation, or fixture content: or is manipulated into
    # busywork still stops. clock is injectable so tests can. It remains unchanged at runtime.
    # Learn string line 5: Literal prompt, documentation, or fixture content: simulate time passing without
    # sleeping.. It remains unchanged at runtime.
    """Run step() until the agent finishes or a limit stops it.

    Limits live here, outside the model: a model that never calls finish, loops,
    or is manipulated into busywork still stops. clock is injectable so tests can
    simulate time passing without sleeping.
    """
    # Learn: Set state to AgentState(goal=goal, grant=grant); the current run goal, permissions, transcript,
    # and denied proposals.
    state = AgentState(goal=goal, grant=grant)
    # Learn: Append one item to the ordered collection on state.transcript; inputs: Entry('goal', goal).
    state.transcript.append(Entry("goal", goal))
    # Learn: Set started to clock(); the monotonic timestamp used to measure elapsed time.
    started = clock()
    # Learn: Iterate over range(max_steps), binding _ for each item.
    for _ in range(max_steps):
        # Learn: Take this branch only if clock() minus started is greater than deadline_seconds.
        if clock() - started > deadline_seconds:
            # Learn: Return state.stop('deadline') to the caller and stop this function.
            return state.stop("deadline")
        # Learn: Set result to step(state, desktop, model); the operation outcome for subsequent checks or
        # reporting.
        result = step(state, desktop, model)
        # Learn: Take this branch only if result is not None (no value).
        if result is not None:
            # Learn: Return result to the caller and stop this function.
            return result
    # Learn: Return state.stop('step_limit') to the caller and stop this function.
    return state.stop("step_limit")
