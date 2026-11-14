"""The desktop interface the agent loop drives, and an in-memory fake.

The real implementation will wrap an E2B desktop. The loop only depends on this
Protocol, so swapping the fake for E2B should not change the loop's logic.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from .page_search import search_passages


@dataclass(frozen=True)
class PageLink:
    label: str
    url: str


@dataclass(frozen=True)
class Observation:
    url: str | None
    text: str
    links: tuple[PageLink, ...] = ()


class Desktop(Protocol):
    def observe(self) -> Observation: ...
    def navigate(self, url: str) -> None: ...
    def search_page(self, query: str) -> Observation: ...


class FakeDesktop:
    """A dict of URL -> page text. Records every navigation that actually ran,
    so tests can assert on effects rather than on what the model intended."""

    def __init__(self, pages: Mapping[str, str], *, links: Mapping[str, tuple[PageLink, ...]] | None = None):
        self.pages = dict(pages)
        self.links = dict(links or {})
        self.url: str | None = None
        self.visited: list[str] = []

    def observe(self) -> Observation:
        if self.url is None:
            return Observation(None, "Blank desktop. No page is open.")
        return Observation(self.url, self.pages.get(self.url, "404 Not Found"),
                           self.links.get(self.url, ()))

    def navigate(self, url: str) -> None:
        self.visited.append(url)
        self.url = url

    def search_page(self, query: str) -> Observation:
        if self.url is None:
            return Observation(None, "No page is open. Navigate to a permitted source first.")
        return Observation(self.url, search_passages(self.pages.get(self.url, "404 Not Found"), query))
