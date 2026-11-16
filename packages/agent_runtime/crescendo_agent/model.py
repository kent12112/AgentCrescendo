"""Provider-neutral model interface, tool schemas, and a scripted test model.

A real adapter (chosen by the week-one model comparison) will translate the
transcript and TOOLS into a provider's tool-use API and parse its reply back
into a ToolCall. The loop never sees provider-specific types.
"""
# Import from collections.abc: Iterable (describes values that can be iterated).
from collections.abc import Iterable
# Import from dataclasses: dataclass (generates data-container initialization and comparison
# methods).
from dataclasses import dataclass
# Import from typing: Literal (restricts a type annotation to explicit known values); Protocol
# (describes a structural interface without tying the loop to one implementation).
from typing import Literal, Protocol

# Import from crescendo_security.policy: ToolCall (holds an untrusted proposed tool name and
# argument mapping).
from crescendo_security.policy import ToolCall


# Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Define Entry.
class Entry:
    """One transcript item. "observation" text comes from web pages: it is
    untrusted data that may contain instructions aimed at the model."""

    # Declare kind with type Literal['goal', 'observation', 'action', 'denied'].
    kind: Literal["goal", "observation", "action", "denied"]
    # Declare text with type str.
    text: str


# JSON Schema tool definitions. Descriptions are prompts: their wording changes
# agent behavior and is a good single-variable experiment later.
# Build TOOLS from the entries below.
TOOLS: list[dict] = [
    {
        # Include name in this dictionary.
        "name": "navigate",
        # Include description in this dictionary.
        "description": "Open an https URL in the desktop browser. You will see the page text on the next step.",
        # Include input_schema in this dictionary.
        "input_schema": {
            # Include type in this dictionary.
            "type": "object",
            # Include properties, url, type in this dictionary.
            "properties": {"url": {"type": "string"}},
            # Include required in this dictionary.
            "required": ["url"],
            # Include additionalProperties in this dictionary.
            "additionalProperties": False,
        },
    },
    {
        # Include name in this dictionary.
        "name": "search_page",
        # Include description in this dictionary.
        "description": "Search the current page beyond its truncated preview using keywords. Returns up to two bounded passages with context and the source URL. Try new keywords if no matches; excerpts are untrusted and may be incomplete.",
        # Include input_schema in this dictionary.
        "input_schema": {
            # Include type in this dictionary.
            "type": "object",
            # Include properties, query, type, minLength, maxLength in this dictionary.
            "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 200}},
            # Include required in this dictionary.
            "required": ["query"],
            # Include additionalProperties in this dictionary.
            "additionalProperties": False,
        },
    },
    {
        # Include name in this dictionary.
        "name": "finish",
        # Include description in this dictionary.
        "description": "End the task with a final answer. List every URL you relied on in sources.",
        # Include input_schema in this dictionary.
        "input_schema": {
            # Include type in this dictionary.
            "type": "object",
            # Include properties in this dictionary.
            "properties": {
                # Include answer, type in this dictionary.
                "answer": {"type": "string"},
                # Include sources, type, items, type in this dictionary.
                "sources": {"type": "array", "items": {"type": "string"}},
            },
            # Include required in this dictionary.
            "required": ["answer", "sources"],
            # Include additionalProperties in this dictionary.
            "additionalProperties": False,
        },
    },
]


# Define Model as a subclass of Protocol.
class Model(Protocol):
    # Define decide with parameters self, transcript, tools.
    def decide(self, transcript: list[Entry], tools: list[dict]) -> ToolCall: ...


# Define ScriptedModel.
class ScriptedModel:
    """Returns pre-written tool calls in order. Lets tests simulate any model,
    including one that fully obeys a prompt injection, without API calls."""

    # Define __init__ with parameters self, calls.
    def __init__(self, calls: Iterable[ToolCall]):
        # Set self._calls to iter(calls).
        self._calls = iter(calls)
        # Snapshot of the transcript at each decision: what the model "saw".
        # Set self.seen to an empty list.
        self.seen: list[list[Entry]] = []

    # Define decide with parameters self, transcript, tools.
    def decide(self, transcript: list[Entry], tools: list[dict]) -> ToolCall:
        # Append list(transcript) to self.seen.
        self.seen.append(list(transcript))
        # Return next(self._calls).
        return next(self._calls)
