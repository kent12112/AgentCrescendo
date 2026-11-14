"""The bounded observe -> decide -> authorize -> act loop for one agent."""
import time
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from crescendo_security.policy import Decision, TaskGrant, ToolCall, authorize

from .desktop import Desktop, Observation
from .model import TOOLS, Entry, Model


@dataclass
class RunResult:
    status: Literal["finished", "step_limit", "deadline"]
    answer: str | None
    sources: list[str]
    transcript: list[Entry]
    denied: list[tuple[ToolCall, Decision]]


@dataclass
class AgentState:
    goal: str
    grant: TaskGrant
    transcript: list[Entry] = field(default_factory=list)
    denied: list[tuple[ToolCall, Decision]] = field(default_factory=list)
    pending_observation: Observation | None = None

    def stop(self, status, answer=None, sources=()) -> RunResult:
        return RunResult(status, answer, list(sources), self.transcript, self.denied)


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
    obs = state.pending_observation if state.pending_observation is not None else desktop.observe()
    state.pending_observation = None
    observation = f"URL: {obs.url}\n{obs.text}"
    if obs.links:
        observation += "\nPage links (untrusted): " + json.dumps([
            {"label": link.label, "url": link.url} for link in obs.links
        ])
    state.transcript.append(Entry("observation", observation))

    # 2. Decide. The model only proposes; it has no ability to act on its own.
    call = model.decide(state.transcript, TOOLS)
    state.transcript.append(Entry("action", f"{call.name} {dict(call.args)}"))

    # 3. Authorize BEFORE acting. If this came after step 4, a denied action
    # would already have happened and the check would only be a log entry.
    decision = authorize(state.grant, call)
    if not decision.allowed:
        state.transcript.append(Entry("denied", decision.reason))
        state.denied.append((call, decision))
        return None

    # 4. Act.
    if call.name == "navigate":
        desktop.navigate(call.args["url"])
        return None
    if call.name == "search_page":
        state.pending_observation = desktop.search_page(call.args["query"])
        return None
    if call.name == "finish":
        return state.stop("finished", call.args["answer"], call.args["sources"])
    raise ValueError(f"Tool '{call.name}' is granted but has no implementation.")


def run_agent(
    goal: str,
    grant: TaskGrant,
    desktop: Desktop,
    model: Model,
    *,
    max_steps: int = 10,
    deadline_seconds: float = 120.0,
    clock: Callable[[], float] = time.monotonic,
) -> RunResult:
    """Run step() until the agent finishes or a limit stops it.

    Limits live here, outside the model: a model that never calls finish, loops,
    or is manipulated into busywork still stops. clock is injectable so tests can
    simulate time passing without sleeping.
    """
    state = AgentState(goal=goal, grant=grant)
    state.transcript.append(Entry("goal", goal))
    started = clock()
    for _ in range(max_steps):
        if clock() - started > deadline_seconds:
            return state.stop("deadline")
        result = step(state, desktop, model)
        if result is not None:
            return result
    return state.stop("step_limit")
