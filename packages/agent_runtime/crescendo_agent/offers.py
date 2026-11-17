"""Offer finder (JOB-F01): turn link IDs the model cites into trusted job-offer records.

The model never writes a title or URL. It finishes with
``{"offers": [{"link_id": 12, "why": "..."}]}``; the host looks each ID up in the
browser's current link snapshot (``E2BDesktop.link_records``) and accepts it only
when the link's real destination is a posting on the same company board the run
started on. Title and URL come from the browser; ``why`` is the model's own,
untrusted account and is shown as such.

Supported boards render without page scripts (probed November 17, 2026):
Greenhouse (job-boards.greenhouse.io) and Lever (jobs.lever.co). Ashby does not.
"""
from dataclasses import dataclass
import json
import re
from urllib.parse import urlsplit

MAX_OFFERS = 5
MAX_WHY_CHARS = 200

GREENHOUSE_HOSTS = frozenset({"job-boards.greenhouse.io", "boards.greenhouse.io"})
LEVER_HOST = "jobs.lever.co"
SLUG = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}"
GREENHOUSE_POSTING = re.compile(rf"^/({SLUG})/jobs/\d{{1,20}}/?$")
LEVER_POSTING = re.compile(rf"^/({SLUG})/[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}/?$")
BOARD_PATH = re.compile(rf"^/({SLUG})/?$")
# Lever's APPLY button links to the same posting page as the title (smoke check,
# November 17, 2026), so the destination alone cannot tell them apart. A card must
# be titled by the posting's own text, so button-word labels are refused.
GENERIC_LABELS = frozenset({"apply", "apply now", "apply for this job", "view job", "view",
                            "details", "learn more", "more", "see job"})


@dataclass(frozen=True)
class Board:
    """A company job board: which platform hosts it and the company's slug there."""

    platform: str  # "greenhouse" or "lever"
    company: str
    url: str


def board_from_url(url: str) -> Board | None:
    """Recognize a supported company board URL (https, no query), else None."""
    parts = urlsplit(url or "")
    match = BOARD_PATH.match(parts.path)
    if parts.scheme != "https" or parts.query or parts.fragment or not match:
        return None
    if parts.hostname in GREENHOUSE_HOSTS:
        return Board("greenhouse", match.group(1).lower(), url)
    if parts.hostname == LEVER_HOST:
        return Board("lever", match.group(1).lower(), url)
    return None


def posting_company(href: str) -> tuple[str, str] | None:
    """(platform, company) when href is a single posting page, else None.

    Query strings are allowed (boards add tracking parameters); application
    pages (Lever's ``/apply``), board pages, and other hosts are not postings.
    """
    parts = urlsplit(href or "")
    if parts.scheme != "https":
        return None
    if parts.hostname in GREENHOUSE_HOSTS:
        match = GREENHOUSE_POSTING.match(parts.path)
        return ("greenhouse", match.group(1).lower()) if match else None
    if parts.hostname == LEVER_HOST:
        match = LEVER_POSTING.match(parts.path)
        return ("lever", match.group(1).lower()) if match else None
    return None


def is_generic_label(label: str) -> bool:
    """True for button words (Apply, View job) that cannot title an offer card."""
    return " ".join((label or "").split()).strip(" →>»").lower() in GENERIC_LABELS


def parse_offer_answer(answer: str, max_offers: int = MAX_OFFERS) -> list[tuple[int, str]]:
    """Parse the model's finish answer into (link_id, why) pairs, or raise ValueError.

    The error text goes back to the model as a denial, so it says how to fix it.
    An empty list is a valid, honest "nothing matched".
    """
    fix = ('Finish with only JSON: {"offers": [{"link_id": <ID from the current visible_links>, '
           f'"why": "<one short sentence>"}}]}}, at most {max_offers} offers.')
    try:
        data = json.loads(answer)
    except (TypeError, ValueError):
        raise ValueError("The answer is not JSON. " + fix) from None
    if not isinstance(data, dict) or set(data) != {"offers"} or not isinstance(data["offers"], list):
        raise ValueError("The answer must be an object with only an offers list. " + fix)
    offers = data["offers"]
    if len(offers) > max_offers:
        raise ValueError(f"Too many offers ({len(offers)}). " + fix)
    pairs, seen = [], set()
    for offer in offers:
        if not isinstance(offer, dict) or set(offer) != {"link_id", "why"}:
            raise ValueError("Each offer needs exactly link_id and why. " + fix)
        link_id, why = offer["link_id"], offer["why"]
        if type(link_id) is not int or link_id < 1:
            raise ValueError("link_id must be a positive integer ID. " + fix)
        if link_id in seen:
            raise ValueError(f"link_id {link_id} is listed twice. " + fix)
        if (not isinstance(why, str) or not why.strip() or len(why) > MAX_WHY_CHARS
                or any(c in why for c in "\r\n")):
            raise ValueError(f"why must be one nonblank line of at most {MAX_WHY_CHARS} characters. " + fix)
        seen.add(link_id)
        pairs.append((link_id, why.strip()))
    return pairs


def offer_validator(desktop, board: Board, accepted: list, *, max_offers: int = MAX_OFFERS):
    """Build a finish_validator for run_vision_agent.

    Returns None (accept) only when every cited ID is in the current snapshot and
    links to a posting on ``board``. On acceptance, ``accepted`` is replaced with
    the trusted offer records; on refusal it is left empty and the reason goes
    back to the model.
    """
    def validate(answer: str) -> str | None:
        accepted.clear()
        try:
            pairs = parse_offer_answer(answer, max_offers)
        except ValueError as error:
            return str(error)
        records = desktop.link_records([link_id for link_id, _ in pairs])
        offers = []
        for link_id, why in pairs:
            record = records.get(link_id)
            if record is None:
                return (f"link_id {link_id} is not a link in the current visible_links. "
                        "Cite only IDs from the latest list.")
            if (posting_company(record["href"]) != (board.platform, board.company)
                    or is_generic_label(record["label"])):
                return (f"link_id {link_id} ({record['label'][:60]!r}) is not a job posting on this "
                        "company's board. Cite the posting's title link, not Apply or navigation links.")
            offers.append({"link_id": link_id, "title": record["label"], "url": record["href"],
                           "company": board.company, "platform": board.platform,
                           "screen_point": [record["x"], record["y"]], "why_untrusted": why})
        accepted[:] = offers
        return None

    return validate


def offer_goal(board: Board, looking_for: str, max_offers: int = MAX_OFFERS) -> str:
    """The task text for one board. looking_for is the user's own words, kept short."""
    if not isinstance(looking_for, str) or not looking_for.strip() or len(looking_for) > 200 \
            or any(c in looking_for for c in "\r\n"):
        raise ValueError("looking_for must be one nonblank line of at most 200 characters.")
    return (f"You are viewing the {board.company} job board on {board.platform}. Find up to "
            f"{max_offers} job postings that best match what the user is looking for: "
            f"{looking_for.strip()!r}. Scroll to see more postings. Do not open application forms. "
            "When the best matches are visible, finish with only JSON: "
            '{"offers": [{"link_id": <ID of the posting title link in the CURRENT visible_links>, '
            '"why": "<one short sentence on the match>"}]}. '
            'If nothing matches, finish with {"offers": []}.')
