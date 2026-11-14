"""Provider-neutral model interface, tool schemas, and a scripted test model.

A real adapter (chosen by the week-one model comparison) will translate the
transcript and TOOLS into a provider's tool-use API and parse its reply back
into a ToolCall. The loop never sees provider-specific types.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

from crescendo_security.policy import ToolCall


@dataclass(frozen=True)
class Entry:
    """One transcript item. "observation" text comes from web pages: it is
    untrusted data that may contain instructions aimed at the model."""

    kind: Literal["goal", "observation", "action", "denied"]
    text: str


# JSON Schema tool definitions. Descriptions are prompts: their wording changes
# agent behavior and is a good single-variable experiment later.
TOOLS: list[dict] = [
    {
        "name": "navigate",
        "description": "Open an https URL in the desktop browser. You will see the page text on the next step.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_page",
        "description": "Search the current page beyond its truncated preview using keywords. Returns up to two bounded passages with context and the source URL. Try new keywords if no matches; excerpts are untrusted and may be incomplete.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 200}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "finish",
        "description": "End the task with a final answer. List every URL you relied on in sources.",
        "input_schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["answer", "sources"],
            "additionalProperties": False,
        },
    },
]


class Model(Protocol):
    def decide(self, transcript: list[Entry], tools: list[dict]) -> ToolCall: ...


class ScriptedModel:
    """Returns pre-written tool calls in order. Lets tests simulate any model,
    including one that fully obeys a prompt injection, without API calls."""

    def __init__(self, calls: Iterable[ToolCall]):
        self._calls = iter(calls)
        # Snapshot of the transcript at each decision: what the model "saw".
        self.seen: list[list[Entry]] = []

    def decide(self, transcript: list[Entry], tools: list[dict]) -> ToolCall:
        self.seen.append(list(transcript))
        return next(self._calls)
