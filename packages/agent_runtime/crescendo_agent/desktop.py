# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
# Learn string line 1: Literal prompt, documentation, or fixture content: The desktop interface the agent
# loop drives, and an in-memory fake.. It remains unchanged at runtime.
# Learn string line 3: Literal prompt, documentation, or fixture content: The real implementation will wrap
# an E2B desktop. The loop only depends on this. It remains unchanged at runtime.
# Learn string line 4: Literal prompt, documentation, or fixture content: Protocol, so swapping the fake for
# E2B should not change the loop's logic.. It remains unchanged at runtime.
"""The desktop interface the agent loop drives, and an in-memory fake.

The real implementation will wrap an E2B desktop. The loop only depends on this
Protocol, so swapping the fake for E2B should not change the loop's logic.
"""
# Learn: From collections.abc, import Mapping (describes key/value access without requiring a concrete
# dict).
from collections.abc import Mapping
# Learn: From dataclasses, import dataclass (generates data-container initialization and comparison
# methods).
from dataclasses import dataclass
# Learn: From typing, import Protocol (describes a structural interface without tying the loop to one
# implementation).
from typing import Protocol

# Learn: From .page_search, import search_passages (finds a bounded selection of lexical matches in
# current-page text).
from .page_search import search_passages


# Learn: Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Learn: Define PageLink. Indented methods and attributes belong to this class.
class PageLink:
    # Learn: Declare label with type str.
    label: str
    # Learn: Declare url with type str; the destination or current page address.
    url: str


# Learn: Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Learn: Define Observation. Indented methods and attributes belong to this class.
class Observation:
    # Learn: Declare url with type str | None; the destination or current page address.
    url: str | None
    # Learn: Declare text with type str.
    text: str
    # Learn: Set links to the tuple () (positional values); the bounded observed links; listing a link does
    # not grant permission to open it.
    links: tuple[PageLink, ...] = ()


# Learn: Define Desktop inheriting Protocol. Indented methods and attributes belong to this class.
class Desktop(Protocol):
    # Learn: Define observe(). The body runs when called, not when defined.
    def observe(self) -> Observation: ...
    # Learn: Define navigate(url). The body runs when called, not when defined.
    def navigate(self, url: str) -> None: ...
    # Learn: Define search_page(query). The body runs when called, not when defined.
    def search_page(self, query: str) -> Observation: ...


# Learn: Define FakeDesktop. Indented methods and attributes belong to this class.
class FakeDesktop:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: A dict of URL -> page text.
    # Records every navigation that actually ran,. It remains unchanged at runtime.
    # Learn string line 2: Literal prompt, documentation, or fixture content: so tests can assert on effects
    # rather than on what the model intended.. It remains unchanged at runtime.
    """A dict of URL -> page text. Records every navigation that actually ran,
    so tests can assert on effects rather than on what the model intended."""

    # Learn: Define __init__(pages, links). This initializes or validates each new instance.
    def __init__(self, pages: Mapping[str, str], *, links: Mapping[str, tuple[PageLink, ...]] | None = None):
        # Learn: Set self.pages to dict(pages).
        self.pages = dict(pages)
        # Learn: Set self.links to dict(links or {}); the bounded observed links; listing a link does not
        # grant permission to open it.
        self.links = dict(links or {})
        # Learn: Set self.url to None (no value); the destination or current page address.
        self.url: str | None = None
        # Learn: Set self.visited to a new list (empty); the successful navigation destinations observed by
        # the adapter.
        self.visited: list[str] = []

    # Learn: Define observe(). The body runs when called, not when defined.
    def observe(self) -> Observation:
        # Learn: Take this branch only if self.url is None (no value).
        if self.url is None:
            # Learn: Return Observation(None, 'Blank desktop. No page is open.') to the caller and stop this
            # function.
            return Observation(None, "Blank desktop. No page is open.")
        # Learn: Return Observation(self.url, self.pages.get(self.url, '404 Not Found'),
        # self.links.get(self.url, ())) to the caller and stop this function.
        return Observation(self.url, self.pages.get(self.url, "404 Not Found"),
                           # Learn: Read a key/row, using the supplied default when applicable on
                           # self.links; inputs: self.url, the tuple () (positional values).
                           self.links.get(self.url, ()))

    # Learn: Define navigate(url). The body runs when called, not when defined.
    def navigate(self, url: str) -> None:
        # Learn: Append one item to the ordered collection on self.visited; inputs: url.
        self.visited.append(url)
        # Learn: Set self.url to url; the destination or current page address.
        self.url = url

    # Learn: Define search_page(query). The body runs when called, not when defined.
    def search_page(self, query: str) -> Observation:
        # Learn: Take this branch only if self.url is None (no value).
        if self.url is None:
            # Learn: Return Observation(None, 'No page is open. Navigate to a permitted source first.') to
            # the caller and stop this function.
            return Observation(None, "No page is open. Navigate to a permitted source first.")
        # Learn: Return Observation(self.url, search_passages(self.pages.get(self.url, '404 Not Found'),
        # query)) to the caller and stop this function.
        return Observation(self.url, search_passages(self.pages.get(self.url, "404 Not Found"), query))
