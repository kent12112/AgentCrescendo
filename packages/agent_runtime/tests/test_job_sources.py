"""Offline tests for ATS posting sources (JOB-F00). httpx.MockTransport replaces the network.

Fixtures copy the field shapes seen live on November 17, 2026 (scripts/fetch_jobs.py).
"""
import json

import httpx
import pytest

from crescendo_agent import job_sources
from crescendo_agent.job_sources import (CompanyBoard, Posting, fetch_board, fetch_boards, html_to_text,
                                         normalize)

LEVER_ID = "6ed76ce8-4156-4b60-b120-403538bd66cd"
ASHBY_ID = "8fb1615c-34bf-47c4-a1d1-b7b2f836bbd3"

GREENHOUSE = {"jobs": [{
    "id": 5456619008, "title": "Backend Engineer", "company_name": "Acme",
    "absolute_url": "https://careers.acme.example/jobs?gh_jid=5456619008",  # custom career site
    "location": {"name": "San Francisco, CA | Seattle, WA"},
    "metadata": [{"name": "Location Type", "value": "On-Site"}],
    "first_published": "2026-10-19T11:17:24-04:00", "updated_at": "2026-10-20T00:00:00-04:00",
    "departments": [{"name": "Engineering"}],
    "content": "&lt;h2&gt;About&lt;/h2&gt;&lt;p&gt;Build &amp;amp; run APIs.&lt;/p&gt;"
               "&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;li&gt;Postgres&lt;/li&gt;&lt;/ul&gt;"
               "&lt;script&gt;alert(1)&lt;/script&gt;"}], "meta": {"total": 1}}

LEVER = [{
    "id": LEVER_ID, "text": "Backend Software Engineer",
    "categories": {"commitment": "Full-time", "location": "New York, NY", "team": "Dev",
                   "allLocations": ["New York, NY", "London"]},
    "createdAt": 1786469891368, "workplaceType": "hybrid",
    "descriptionPlain": "The Role\n\xa0\nBuild systems.",
    "lists": [{"text": "Requirements", "content": "<li>Python</li><li>Distributed systems</li>"}],
    "additionalPlain": "Visa sponsorship available.",
    "salaryRange": {"currency": "USD", "interval": "per-year-salary", "min": 150000, "max": 200000},
    "hostedUrl": f"https://jobs.lever.co/acme/{LEVER_ID}"}]

ASHBY = {"apiVersion": "1", "jobs": [
    {"id": ASHBY_ID, "title": "Research Engineer", "department": "Research", "employmentType": "FullTime",
     "location": "San Francisco", "secondaryLocations": [{"location": "New York City"}],
     "isListed": True, "isRemote": True, "workplaceType": "Hybrid",
     "publishedAt": "2026-11-05T02:20:02.702+00:00", "descriptionPlain": "ABOUT THE TEAM\n\nWe train models.",
     "compensation": {"compensationTierSummary": "$250K – $445K • Offers Equity"},
     "jobUrl": "https://evil.example/phish"},
    {"id": "1ae64ddb-505f-4ad2-a731-3a857e94edee", "title": "", "isListed": True},   # blank title (seen live)
    {"id": "2ae64ddb-505f-4ad2-a731-3a857e94edee", "title": "Hidden", "isListed": False},
]}


def client_for(routes):
    """routes: {url: (status, body bytes or JSON-able)}; unknown URLs fail the test."""
    def handle(request):
        status, body = routes[str(request.url)]
        content = body if isinstance(body, bytes) else json.dumps(body).encode()
        return httpx.Response(status, content=content)
    return httpx.Client(transport=httpx.MockTransport(handle))


@pytest.mark.parametrize("spec, expected", [
    ("lever:palantir", CompanyBoard("lever", "palantir")),
    (" Greenhouse:anthropic ", CompanyBoard("greenhouse", "anthropic")),
    ("ashby:openai", CompanyBoard("ashby", "openai")),
])
def test_parse_board(spec, expected):
    assert CompanyBoard.parse(spec) == expected


@pytest.mark.parametrize("spec", ["workday:acme", "lever:", "lever", "lever:../x", "lever:a/b",
                                  "lever:a?b=1", "lever:" + "a" * 101, "", "greenhouse:-acme"])
def test_parse_board_refuses_anything_that_could_reshape_the_url(spec):
    with pytest.raises(ValueError):
        CompanyBoard.parse(spec)


def test_api_urls():
    assert CompanyBoard("greenhouse", "acme").api_url == \
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"
    assert CompanyBoard("lever", "acme").api_url == "https://api.lever.co/v0/postings/acme?mode=json"
    assert CompanyBoard("ashby", "acme").api_url == \
        "https://api.ashbyhq.com/posting-api/job-board/acme?includeCompensation=true"


def test_greenhouse_normalized_and_url_rebuilt():
    result = normalize(CompanyBoard("greenhouse", "acme"), GREENHOUSE)
    assert result.error is None and result.skipped == 0
    (posting,) = result.postings
    assert posting == Posting(
        source="greenhouse", company="acme", posting_id="5456619008", title="Backend Engineer",
        url="https://job-boards.greenhouse.io/acme/jobs/5456619008",
        locations=("San Francisco, CA", "Seattle, WA"), workplace="onsite", department="Engineering",
        published_at="2026-10-19T15:17:24Z", description="About\nBuild & run APIs.\n- Python\n- Postgres",
        company_name="Acme")


def test_lever_normalized():
    (posting,) = normalize(CompanyBoard("lever", "acme"), LEVER).postings
    assert posting.url == f"https://jobs.lever.co/acme/{LEVER_ID}"
    assert posting.locations == ("New York, NY", "London")
    assert (posting.workplace, posting.department, posting.employment_type) == ("hybrid", "Dev", "Full-time")
    assert posting.published_at.startswith("2026-08-")
    assert posting.compensation == "USD 150,000–200,000 per-year-salary"
    assert posting.description == ("The Role\nBuild systems.\n\nRequirements\n- Python\n- Distributed systems"
                                   "\n\nVisa sponsorship available.")


def test_ashby_skips_unlisted_and_blank_and_ignores_response_urls():
    result = normalize(CompanyBoard("ashby", "acme"), ASHBY)
    assert result.skipped == 2
    (posting,) = result.postings
    assert posting.url == f"https://jobs.ashbyhq.com/acme/{ASHBY_ID}"  # never the response's jobUrl
    assert posting.locations == ("San Francisco", "New York City")
    assert posting.workplace == "hybrid" and posting.compensation == "$250K – $445K • Offers Equity"
    assert posting.published_at == "2026-11-05T02:20:02.702000Z"


@pytest.mark.parametrize("source, item", [
    ("greenhouse", {"id": "12; rm", "title": "x"}),
    ("greenhouse", {"id": 1, "title": "   "}),
    ("lever", {"id": "../../etc", "text": "x"}),
    ("ashby", {"id": ASHBY_ID.upper(), "title": "x"}),
    ("ashby", "not an object"),
])
def test_bad_items_are_skipped_not_raised(source, item):
    data = [item] if source == "lever" else {"jobs": [item]}
    result = normalize(CompanyBoard(source, "acme"), data)
    assert result.postings == [] and result.skipped == 1


def test_duplicate_ids_are_counted_once():
    result = normalize(CompanyBoard("lever", "acme"), LEVER * 2)
    assert len(result.postings) == 1 and result.skipped == 1


@pytest.mark.parametrize("source, data", [("lever", {"jobs": []}), ("greenhouse", []),
                                          ("ashby", {"jobs": "x"}), ("greenhouse", None)])
def test_wrong_shape_is_an_error(source, data):
    assert normalize(CompanyBoard(source, "acme"), data).error == "The response did not contain a job list."


def test_long_and_odd_text_is_bounded():
    text = html_to_text("<p>" + "word " * 10000 + "</p><style>p{}</style>")
    assert len(text) == job_sources.MAX_DESCRIPTION_CHARS and "p{}" not in text
    item = dict(LEVER[0], text="T" * 1000, createdAt="not a date")
    (posting,) = normalize(CompanyBoard("lever", "acme"), [item]).postings
    assert len(posting.title) == job_sources.MAX_FIELD_CHARS and posting.published_at is None


def test_fetch_board_success_and_errors():
    board = CompanyBoard("lever", "acme")
    ok = fetch_board(board, client_for({board.api_url: (200, LEVER)}))
    assert ok.error is None and len(ok.postings) == 1
    for status, body, words in [(404, b"Not Found", "No public job board"),
                                (500, b"oops", "HTTP 500"),
                                (200, b"<html>", "not valid JSON"),
                                (302, b"", "HTTP 302")]:
        result = fetch_board(board, client_for({board.api_url: (status, body)}))
        assert words in result.error and result.postings == []


def test_fetch_board_enforces_size_limit(monkeypatch):
    monkeypatch.setattr(job_sources, "MAX_RESPONSE_BYTES", 100)
    board = CompanyBoard("lever", "acme")
    result = fetch_board(board, client_for({board.api_url: (200, LEVER)}))
    assert result.error == "The response is larger than the size limit."


def test_fetch_board_network_failures_do_not_raise():
    def boom(request):
        raise httpx.ConnectError("refused", request=request)

    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    board = CompanyBoard("ashby", "acme")
    assert fetch_board(board, httpx.Client(transport=httpx.MockTransport(boom))).error == \
        "Network error (ConnectError)."
    assert fetch_board(board, httpx.Client(transport=httpx.MockTransport(slow))).error == \
        "The job board API timed out."


def test_fetch_boards_keeps_going_after_one_failure():
    good, bad = CompanyBoard("greenhouse", "acme"), CompanyBoard("lever", "gone")
    results = fetch_boards([bad, good], client_for({bad.api_url: (404, b""), good.api_url: (200, GREENHOUSE)}))
    assert [r.error is None for r in results] == [False, True]
    assert results[1].postings[0].title == "Backend Engineer"
