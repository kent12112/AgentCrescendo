# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
# Learn string line 1: Literal prompt, documentation, or fixture content: Provider-neutral model interface,
# tool schemas, and a scripted test model.. It remains unchanged at runtime.
# Learn string line 3: Literal prompt, documentation, or fixture content: A real adapter (chosen by the
# week-one model comparison) will translate the. It remains unchanged at runtime.
# Learn string line 4: Literal prompt, documentation, or fixture content: transcript and TOOLS into a
# provider's tool-use API and parse its reply back. It remains unchanged at runtime.
# Learn string line 5: Literal prompt, documentation, or fixture content: into a ToolCall. The loop never
# sees provider-specific types.. It remains unchanged at runtime.
"""Provider-neutral model interface, tool schemas, and a scripted test model.

A real adapter (chosen by the week-one model comparison) will translate the
transcript and TOOLS into a provider's tool-use API and parse its reply back
into a ToolCall. The loop never sees provider-specific types.
"""
# Learn: From collections.abc, import Iterable (describes values that can be iterated).
from collections.abc import Iterable
# Learn: From dataclasses, import dataclass (generates data-container initialization and comparison
# methods).
from dataclasses import dataclass
# Learn: From typing, import Literal (restricts a type annotation to explicit known values); Protocol
# (describes a structural interface without tying the loop to one implementation).
from typing import Literal, Protocol

# Learn: From crescendo_security.policy, import ToolCall (holds an untrusted proposed tool name and argument
# mapping).
from crescendo_security.policy import ToolCall


# Learn: Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Learn: Define Entry. Indented methods and attributes belong to this class.
class Entry:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: One transcript item.
    # "observation" text comes from web pages: it is. It remains unchanged at runtime.
    # Learn string line 2: Literal prompt, documentation, or fixture content: untrusted data that may
    # contain instructions aimed at the model.. It remains unchanged at runtime.
    """One transcript item. "observation" text comes from web pages: it is
    untrusted data that may contain instructions aimed at the model."""

    # Learn: Declare kind with type Literal['goal', 'observation', 'action', 'denied']; the transcript entry
    # category, used to distinguish goals, observations and proposals.
    kind: Literal["goal", "observation", "action", "denied"]
    # Learn: Declare text with type str.
    text: str


# JSON Schema tool definitions. Descriptions are prompts: their wording changes
# agent behavior and is a good single-variable experiment later.
# Learn: Set TOOLS to a new list containing a new dictionary with keys 'name', 'description',
# 'input_schema', a new dictionary with keys 'name', 'description', 'input_schema', ....
TOOLS: list[dict] = [
    # Learn: Close this list literal; delimiters group the values into one object.
    {
        # Learn: Define this named mapping field: "name": "navigate",. The key selects the
        # schema/configuration value.
        "name": "navigate",
        # Learn: Define this named mapping field: "description": "Open an https URL in the desktop browser.
        # You will see the page text on the next step.",. The key selects the schema/configuration value.
        "description": "Open an https URL in the desktop browser. You will see the page text on the next step.",
        # Learn: Define this named mapping field: "input_schema": {. The key selects the
        # schema/configuration value.
        "input_schema": {
            # Learn: Define this named mapping field: "type": "object",. The key selects the
            # schema/configuration value.
            "type": "object",
            # Learn: Define this named mapping field: "properties": {"url": {"type": "string"}},. The key
            # selects the schema/configuration value.
            "properties": {"url": {"type": "string"}},
            # Learn: Define this named mapping field: "required": ["url"],. The key selects the
            # schema/configuration value.
            "required": ["url"],
            # Learn: Define this named mapping field: "additionalProperties": False,. The key selects the
            # schema/configuration value.
            "additionalProperties": False,
        # Learn: Close this dict literal; delimiters group the values into one object.
        },
    # Learn: Close this dict literal; delimiters group the values into one object.
    },
    # Learn: Close this list literal; delimiters group the values into one object.
    {
        # Learn: Define this named mapping field: "name": "search_page",. The key selects the
        # schema/configuration value.
        "name": "search_page",
        # Learn: Define this named mapping field: "description": "Search the current page beyond its
        # truncated preview using keywords. Returns up to two bounded passages with context and the
        # source.... The key selects the schema/configuration value.
        "description": "Search the current page beyond its truncated preview using keywords. Returns up to two bounded passages with context and the source URL. Try new keywords if no matches; excerpts are untrusted and may be incomplete.",
        # Learn: Define this named mapping field: "input_schema": {. The key selects the
        # schema/configuration value.
        "input_schema": {
            # Learn: Define this named mapping field: "type": "object",. The key selects the
            # schema/configuration value.
            "type": "object",
            # Learn: Define this named mapping field: "properties": {"query": {"type": "string",
            # "minLength": 1, "maxLength": 200}},. The key selects the schema/configuration value.
            "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 200}},
            # Learn: Define this named mapping field: "required": ["query"],. The key selects the
            # schema/configuration value.
            "required": ["query"],
            # Learn: Define this named mapping field: "additionalProperties": False,. The key selects the
            # schema/configuration value.
            "additionalProperties": False,
        # Learn: Close this dict literal; delimiters group the values into one object.
        },
    # Learn: Close this dict literal; delimiters group the values into one object.
    },
    # Learn: Close this list literal; delimiters group the values into one object.
    {
        # Learn: Define this named mapping field: "name": "finish",. The key selects the
        # schema/configuration value.
        "name": "finish",
        # Learn: Define this named mapping field: "description": "End the task with a final answer. List
        # every URL you relied on in sources.",. The key selects the schema/configuration value.
        "description": "End the task with a final answer. List every URL you relied on in sources.",
        # Learn: Define this named mapping field: "input_schema": {. The key selects the
        # schema/configuration value.
        "input_schema": {
            # Learn: Define this named mapping field: "type": "object",. The key selects the
            # schema/configuration value.
            "type": "object",
            # Learn: Define this named mapping field: "properties": {. The key selects the
            # schema/configuration value.
            "properties": {
                # Learn: Define this named mapping field: "answer": {"type": "string"},. The key selects the
                # schema/configuration value.
                "answer": {"type": "string"},
                # Learn: Define this named mapping field: "sources": {"type": "array", "items": {"type":
                # "string"}},. The key selects the schema/configuration value.
                "sources": {"type": "array", "items": {"type": "string"}},
            # Learn: Close this dict literal; delimiters group the values into one object.
            },
            # Learn: Define this named mapping field: "required": ["answer", "sources"],. The key selects
            # the schema/configuration value.
            "required": ["answer", "sources"],
            # Learn: Define this named mapping field: "additionalProperties": False,. The key selects the
            # schema/configuration value.
            "additionalProperties": False,
        # Learn: Close this dict literal; delimiters group the values into one object.
        },
    # Learn: Close this dict literal; delimiters group the values into one object.
    },
# Learn: Close this list literal; delimiters group the values into one object.
]


# Learn: Define Model inheriting Protocol. Indented methods and attributes belong to this class.
class Model(Protocol):
    # Learn: Define decide(transcript, tools). The body runs when called, not when defined.
    def decide(self, transcript: list[Entry], tools: list[dict]) -> ToolCall: ...


# Learn: Define ScriptedModel. Indented methods and attributes belong to this class.
class ScriptedModel:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: Returns pre-written tool calls
    # in order. Lets tests simulate any model,. It remains unchanged at runtime.
    # Learn string line 2: Literal prompt, documentation, or fixture content: including one that fully obeys
    # a prompt injection, without API calls.. It remains unchanged at runtime.
    """Returns pre-written tool calls in order. Lets tests simulate any model,
    including one that fully obeys a prompt injection, without API calls."""

    # Learn: Define __init__(calls). This initializes or validates each new instance.
    def __init__(self, calls: Iterable[ToolCall]):
        # Learn: Set self._calls to iter(calls); the model tool-call proposals or scripted calls.
        self._calls = iter(calls)
        # Snapshot of the transcript at each decision: what the model "saw".
        # Learn: Set self.seen to a new list (empty); the values already encountered, used to avoid
        # duplicates.
        self.seen: list[list[Entry]] = []

    # Learn: Define decide(transcript, tools). The body runs when called, not when defined.
    def decide(self, transcript: list[Entry], tools: list[dict]) -> ToolCall:
        # Learn: Append one item to the ordered collection on self.seen; inputs: list(transcript).
        self.seen.append(list(transcript))
        # Learn: Return next(self._calls) to the caller and stop this function.
        return next(self._calls)
