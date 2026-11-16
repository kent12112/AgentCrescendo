"""The bounded observe -> decide -> authorize -> act loop for one agent."""
# Import time: measures monotonic elapsed time and provides bounded pauses.
import time
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import from collections.abc: Callable (describes a function-valued input such as an injected
# clock).
from collections.abc import Callable
# Import from dataclasses: dataclass (generates data-container initialization and comparison
# methods); field (configures a dataclass field, including per-instance factories and repr hiding).
from dataclasses import dataclass, field
# Import from typing: Literal (restricts a type annotation to explicit known values).
from typing import Literal

# Import from crescendo_security.policy: Decision (holds an allow/deny result and a safe
# explanation); TaskGrant (holds the task identity and immutable tool/host allowlists); ToolCall
# (holds an untrusted proposed tool name and argument mapping); authorize (checks task grants and
# argument bounds before a proposed tool can execute).
from crescendo_security.policy import Decision, TaskGrant, ToolCall, authorize

# Import from .desktop: Desktop (the structural text-browser interface used by the loop);
# Observation (holds current page URL, bounded text, and observed links).
from .desktop import Desktop, Observation
# Import from .model: TOOLS (the text-loop tool schemas offered to the model); Entry (represents one
# typed transcript item sent to the model); Model (the provider-neutral structural decision
# interface).
from .model import TOOLS, Entry, Model


# Decorate the class with generated data-container methods.
@dataclass
# Define RunResult.
class RunResult:
    # Declare status with type Literal['finished', 'step_limit', 'deadline', 'rate_limited'].
    status: Literal["finished", "step_limit", "deadline", "rate_limited"]
    # Declare answer with type str | None.
    answer: str | None
    # Declare sources with type list[str].
    sources: list[str]
    # Declare transcript with type list[Entry].
    transcript: list[Entry]
    # Declare denied with type list[tuple[ToolCall, Decision]].
    denied: list[tuple[ToolCall, Decision]]


# Decorate the class with generated data-container methods.
@dataclass
# Define AgentState.
class AgentState:
    # Declare goal with type str.
    goal: str
    # Declare grant with type TaskGrant.
    grant: TaskGrant
    # Set transcript to field(default_factory=list).
    transcript: list[Entry] = field(default_factory=list)
    # Set denied to field(default_factory=list).
    denied: list[tuple[ToolCall, Decision]] = field(default_factory=list)
    # Set pending_observation to None.
    pending_observation: Observation | None = None

    # Define stop with parameters self, status, answer, sources.
    def stop(self, status, answer=None, sources=()) -> RunResult:
        # Return RunResult(status, answer, list(sources), self.transcript, self.denied).
        return RunResult(status, answer, list(sources), self.transcript, self.denied)


# Define step with parameters state, desktop, model.
def step(state: AgentState, desktop: Desktop, model: Model) -> RunResult | None:
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
    # Set obs to state.pending_observation if state.pending_observation is not None, otherwise
    # desktop.observe().
    obs = state.pending_observation if state.pending_observation is not None else desktop.observe()
    # Set state.pending_observation to None.
    state.pending_observation = None
    # Set observation to f'URL: {obs.url}\n{obs.text}'.
    observation = f"URL: {obs.url}\n{obs.text}"
    # Check whether obs.links.
    if obs.links:
        # Update observation using its previous value plus '\nPage links (untrusted): ' plus
        # json.dumps([{'label': link.label, 'url': link.url} for link in obs.links]).
        observation += "\nPage links (untrusted): " + json.dumps([
            {"label": link.label, "url": link.url} for link in obs.links
        ])
    # Append Entry('observation', observation) to state.transcript.
    state.transcript.append(Entry("observation", observation))

    # 2. Decide. The model only proposes; it has no ability to act on its own.
    # Set call to model.decide(state.transcript, TOOLS).
    call = model.decide(state.transcript, TOOLS)
    # Append Entry('action', f'{call.name} {dict(call.args)}') to state.transcript.
    state.transcript.append(Entry("action", f"{call.name} {dict(call.args)}"))

    # 3. Authorize BEFORE acting. If this came after step 4, a denied action
    # would already have happened and the check would only be a log entry.
    # Set decision to authorize(state.grant, call).
    decision = authorize(state.grant, call)
    # Check whether not (decision.allowed).
    if not decision.allowed:
        # Append Entry('denied', decision.reason) to state.transcript.
        state.transcript.append(Entry("denied", decision.reason))
        # Append (call, decision) to state.denied.
        state.denied.append((call, decision))
        # Return None.
        return None

    # 4. Act.
    # Check whether call.name equals 'navigate'.
    if call.name == "navigate":
        # Call desktop.navigate with call.args['url'].
        desktop.navigate(call.args["url"])
        # Return None.
        return None
    # Check whether call.name equals 'search_page'.
    if call.name == "search_page":
        # Set state.pending_observation to desktop.search_page(call.args['query']).
        state.pending_observation = desktop.search_page(call.args["query"])
        # Return None.
        return None
    # Check whether call.name equals 'finish'.
    if call.name == "finish":
        # Return state.stop('finished', call.args['answer'], call.args['sources']).
        return state.stop("finished", call.args["answer"], call.args["sources"])
    # Raise ValueError(f"Tool '{call.name}' is granted but has no implementation.") to stop the
    # normal path.
    raise ValueError(f"Tool '{call.name}' is granted but has no implementation.")


# Define run_agent with parameters goal, grant, desktop, model, max_steps, deadline_seconds, clock.
def run_agent(
    goal: str,
    grant: TaskGrant,
    desktop: Desktop,
    model: Model,
    # Parameters after * must be passed by keyword, which makes optional controls explicit.
    *,
    # Set max_steps to (10,).
    max_steps: int = 10,
    # Set deadline_seconds to (120.0,).
    deadline_seconds: float = 120.0,
    # Set clock to (time.monotonic,).
    clock: Callable[[], float] = time.monotonic,
) -> RunResult:
    """Run step() until the agent finishes or a limit stops it.

    Limits live here, outside the model: a model that never calls finish, loops,
    or is manipulated into busywork still stops. clock is injectable so tests can
    simulate time passing without sleeping.
    """
    # Set state to AgentState(goal=goal, grant=grant).
    state = AgentState(goal=goal, grant=grant)
    # Append Entry('goal', goal) to state.transcript.
    state.transcript.append(Entry("goal", goal))
    # Set started to clock().
    started = clock()
    # Iterate over range(max_steps), binding _ for each item.
    for _ in range(max_steps):
        # Check whether clock() minus started is greater than deadline_seconds.
        if clock() - started > deadline_seconds:
            # Return state.stop('deadline').
            return state.stop("deadline")
        # Set result to step(state, desktop, model).
        result = step(state, desktop, model)
        # Check whether result is not None.
        if result is not None:
            # Return result.
            return result
    # Return state.stop('step_limit').
    return state.stop("step_limit")
