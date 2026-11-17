"""Find company job boards to search (JOB-F02), so the user never maintains a list.

ATS APIs answer "what jobs does this company have?", not "which companies have
these jobs?". Sources of company boards:

- Hacker News "Ask HN: Who is hiring?" threads, through the official Algolia HN API
  (free, no key). Top-level comments often link Greenhouse, Lever, or Ashby boards.
  November 2026's thread linked 30 distinct boards.
- An optional local file of ``source:company`` lines the user adds.

Comment text is untrusted: only links matching the three ATS URL shapes are kept,
and every slug passes ``CompanyBoard.parse``. No resume data is sent anywhere.
"""
from html import unescape
import json
import re
from pathlib import Path

from .job_sources import CompanyBoard

HN_SEARCH = ("https://hn.algolia.com/api/v1/search_by_date"
             "?tags=story,author_whoishiring&hitsPerPage=40")  # ~3 thread kinds per month
HN_ITEM = "https://hn.algolia.com/api/v1/items/{id}"
HN_TITLE = re.compile(r"^Ask HN: Who is hiring\? \(([A-Z][a-z]+ \d{4})\)$")
MAX_HN_BYTES = 8 * 1024 * 1024  # One month's thread is ~450 KB.
TIMEOUT_SECONDS = 20.0

ATS_LINK = re.compile(
    r"https?://(?:(?:job-boards|boards)\.greenhouse\.io/(?P<greenhouse>[A-Za-z0-9_.-]+)"
    r"|jobs\.lever\.co/(?P<lever>[A-Za-z0-9_.-]+)"
    r"|jobs\.ashbyhq\.com/(?P<ashby>[A-Za-z0-9_.-]+))")
# Greenhouse paths that are not company boards.
NOT_BOARDS = {"embed", "jobs", "v1"}


def boards_in_text(text: str) -> list[CompanyBoard]:
    """ATS company boards linked in text (HTML allowed), in first-seen order."""
    found = []
    for match in ATS_LINK.finditer(unescape(text or "")):
        source = next(name for name in ("greenhouse", "lever", "ashby") if match.group(name))
        slug = match.group(source).rstrip(".").lower()
        if slug in NOT_BOARDS:
            continue
        try:
            board = CompanyBoard.parse(f"{source}:{slug}")
        except ValueError:
            continue
        if board not in found:
            found.append(board)
    return found


def read_boards_file(path) -> list[CompanyBoard]:
    """One ``source:company`` per line; ``#`` starts a comment. Raises ValueError on a bad line."""
    boards = []
    for number, line in enumerate(Path(path).read_text().splitlines(), start=1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            board = CompanyBoard.parse(line)
        except ValueError as error:
            raise ValueError(f"{path}:{number}: {error}") from None
        if board not in boards:
            boards.append(board)
    return boards


class _HNError(Exception):
    """An HTTP status or size problem; the message is shown as is."""


def _get_json(client, url):
    with client.stream("GET", url, timeout=TIMEOUT_SECONDS, follow_redirects=False) as response:
        if response.status_code != 200:
            raise _HNError(f"HN API answered HTTP {response.status_code}.")
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > MAX_HN_BYTES:
                raise _HNError("HN API response is larger than the size limit.")
    return json.loads(body)


def hn_hiring_boards(client, months: int = 3) -> tuple[list[CompanyBoard], list[str], str | None]:
    """Boards linked from the latest ``months`` "Who is hiring?" threads.

    Returns (boards, thread labels used, error). Never raises for network/data errors.
    """
    import httpx

    if type(months) is not int or not 1 <= months <= 12:
        raise ValueError("months must be an integer from 1 to 12.")
    try:
        hits = _get_json(client, HN_SEARCH).get("hits") or []
        threads = []
        for hit in hits:
            match = HN_TITLE.match(str(hit.get("title", ""))) if isinstance(hit, dict) else None
            if match and str(hit.get("objectID", "")).isdigit():
                threads.append((hit["objectID"], match.group(1)))
        threads = threads[:months]
        if not threads:
            return [], [], "No 'Who is hiring?' threads were found."
        boards, labels = [], []
        for story_id, label in threads:
            item = _get_json(client, HN_ITEM.format(id=story_id))
            for comment in item.get("children") or []:
                if isinstance(comment, dict):
                    for board in boards_in_text(comment.get("text") or ""):
                        if board not in boards:
                            boards.append(board)
            labels.append(label)
        return boards, labels, None
    except _HNError as error:
        return [], [], str(error)
    except httpx.TimeoutException:
        return [], [], "The HN API timed out."
    except httpx.HTTPError as error:
        return [], [], f"HN API network error ({type(error).__name__})."
    except (ValueError, AttributeError) as error:
        return [], [], f"HN API data problem: {error}"
