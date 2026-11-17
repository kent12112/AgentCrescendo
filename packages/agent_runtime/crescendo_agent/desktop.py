"""The desktop interface the agent loop drives, and an in-memory fake.

The real implementation will wrap an E2B desktop. The loop only depends on this
Protocol, so swapping the fake for E2B should not change the loop's logic.
"""
# Import from collections.abc: Mapping (describes key/value access without requiring a concrete
# dict).
from collections.abc import Mapping
# Import from dataclasses: dataclass (generates data-container initialization and comparison
# methods).
from dataclasses import dataclass
# Import from typing: Protocol (describes a structural interface without tying the loop to one
# implementation).
from typing import Protocol

# Import from .page_search: search_passages (finds a bounded selection of lexical matches in
# current-page text).
from .page_search import search_passages


# Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Define PageLink.
class PageLink:
    # Declare label with type str.
    label: str
    # Declare url with type str.
    url: str


# Decorate the class with generated data-container methods; frozen=True prevents attribute
# reassignment.
@dataclass(frozen=True)
# Define Observation.
class Observation:
    # Declare url with type str | None.
    url: str | None
    # Declare text with type str.
    text: str
    # Set links to ().
    links: tuple[PageLink, ...] = ()


class ActionDenied(ValueError):
    """The desktop refused an action after checking the live page. The message is a
    short, safe reason the agent may see so it can choose something else."""


# Define Desktop as a subclass of Protocol.
class Desktop(Protocol):
    # Define observe with parameters self.
    def observe(self) -> Observation: ...
    # Define navigate with parameters self, url.
    def navigate(self, url: str) -> None: ...
    # Define search_page with parameters self, query.
    def search_page(self, query: str) -> Observation: ...


# Define FakeDesktop.
class FakeDesktop:
    """A dict of URL -> page text. Records every navigation that actually ran,
    so tests can assert on effects rather than on what the model intended."""

    # Define __init__ with parameters self, pages, links.
    def __init__(self, pages: Mapping[str, str], *, links: Mapping[str, tuple[PageLink, ...]] | None = None):
        # Set self.pages to dict(pages).
        self.pages = dict(pages)
        # Set self.links to dict(links or {}).
        self.links = dict(links or {})
        # Set self.url to None.
        self.url: str | None = None
        # Set self.visited to an empty list.
        self.visited: list[str] = []

    # Define observe with parameters self.
    def observe(self) -> Observation:
        # Check whether self.url is None.
        if self.url is None:
            # Return Observation(None, 'Blank desktop. No page is open.').
            return Observation(None, "Blank desktop. No page is open.")
        # Return Observation(self.url, self.pages.get(self.url, '404 Not Found'),
        # self.links.get(self.url, ())).
        return Observation(self.url, self.pages.get(self.url, "404 Not Found"),
                           # Read a key/row, using the supplied default when applicable on
                           # self.links; inputs: self.url, the tuple () (positional values).
                           self.links.get(self.url, ()))

    # Define navigate with parameters self, url.
    def navigate(self, url: str) -> None:
        # Append url to self.visited.
        self.visited.append(url)
        # Set self.url to url.
        self.url = url

    # Define search_page with parameters self, query.
    def search_page(self, query: str) -> Observation:
        # Check whether self.url is None.
        if self.url is None:
            # Return Observation(None, 'No page is open. Navigate to a permitted source first.').
            return Observation(None, "No page is open. Navigate to a permitted source first.")
        # Return Observation(self.url, search_passages(self.pages.get(self.url, '404 Not Found'),
        # query)).
        return Observation(self.url, search_passages(self.pages.get(self.url, "404 Not Found"), query))
