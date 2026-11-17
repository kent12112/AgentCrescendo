"""Offline tests for JOB-F06: Common Crawl company discovery, local caches, country filter."""
import json

import httpx
import pytest

from crescendo_agent.common_crawl import (COLLECTIONS_URL, CrawlError, _get, crawl_boards, slug_from_url,
                                          slugs_in_index_text)
from crescendo_agent.job_cache import JobCache, fetch_boards_cached
from crescendo_agent.job_match import posting_countries, rank
from crescendo_agent.job_sources import BoardResult, CompanyBoard, Posting, normalize, normalize_country

UUID = "8fb1615c-34bf-47c4-a1d1-b7b2f836bbd3"


# --- Slugs from crawled URLs ---


@pytest.mark.parametrize("url, slug", [
    (f"https://jobs.ashbyhq.com/1password/{UUID}", "1password"),
    (f"https://jobs.ashbyhq.com/0g/{UUID}?utm_source=Longhash+job+board&utm_medium=getro.com", "0g"),
    ("https://jobs.ashbyhq.com/115ventures", "115ventures"),
    ("https://jobs.ashbyhq.com/Notion/x", "notion"),                       # lowercased: one board
    ("http://jobs.ashbyhq.com/acme/", "acme"),
    ("https://jobs.ashbyhq.com/", None),
    ("https://jobs.ashbyhq.com/api/non-user-graphql", None),               # Ashby's own route
    ("https://jobs.ashbyhq.com/meeting/abc", None),
    ("https://jobs.ashbyhq.com/$10.2K", None),                             # junk seen in Wayback output
    ("https://jobs.ashbyhq.com/%22ddRumClientToken%22:%22pub1%22", None),
    ("https://evil.example/jobs.ashbyhq.com/acme", None),                  # wrong host
    ("https://jobs.ashbyhq.com.evil.example/acme", None),
    ("ftp://jobs.ashbyhq.com/acme", None),
])
def test_slug_from_url(url, slug):
    assert slug_from_url("ashby", url) == slug


def test_slugs_in_index_text_accepts_cdx_line_shapes():
    text = "\n".join([
        f'com,ashbyhq,jobs)/0g/x 20261006024916 {{"url": "https://jobs.ashbyhq.com/0g/{UUID}"}}',  # default
        '{"url": "https://jobs.ashbyhq.com/1x/abc"}',                                             # output=json
        "https://jobs.ashbyhq.com/acme",                                                         # bare URL
        '{"url": "https://jobs.ashbyhq.com/1x/def"}',                                             # duplicate
        "not json {", '{"url": 5}', "", "garbage line"])
    assert slugs_in_index_text("ashby", text) == {"0g", "1x", "acme"}


# --- Index requests ---


def cc_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_get_retries_load_shedding_then_succeeds():
    calls, waits = [], []

    def handle(request):
        calls.append(1)
        return httpx.Response(504 if len(calls) < 3 else 200, text="ok",
                              headers={"retry-after": "7"} if len(calls) == 1 else {})

    assert _get(cc_client(handle), "https://index.commoncrawl.org/x", sleep=waits.append) == b"ok"
    assert waits == [7.0, 30.0]          # Retry-After honored, then the default ladder


def test_get_gives_up_and_404_means_no_captures():
    waits = []
    with pytest.raises(CrawlError, match="HTTP 502"):
        _get(cc_client(lambda r: httpx.Response(502)), "https://index.commoncrawl.org/x", sleep=waits.append)
    assert waits == [15.0, 30.0, 60.0]
    assert _get(cc_client(lambda r: httpx.Response(404)), "https://index.commoncrawl.org/x", sleep=waits.append) is None
    with pytest.raises(CrawlError, match="HTTP 403"):  # not a load-shedding status: no retry
        _get(cc_client(lambda r: httpx.Response(403)), "https://index.commoncrawl.org/x", sleep=lambda s: None)


def test_get_caps_retry_after_and_size(monkeypatch):
    waits = []
    with pytest.raises(CrawlError):
        _get(cc_client(lambda r: httpx.Response(503, headers={"retry-after": "9999"})),
             "https://index.commoncrawl.org/x", sleep=waits.append)
    assert max(waits) == 120.0
    monkeypatch.setattr("crescendo_agent.common_crawl.MAX_BYTES", 10)
    with pytest.raises(CrawlError, match="size limit"):
        _get(cc_client(lambda r: httpx.Response(200, content=b"x" * 11)), "https://index.commoncrawl.org/x",
             sleep=lambda s: None)


def crawl_handler(pages_by_index, fail=()):
    seen = []

    def handle(request):
        url = str(request.url)
        seen.append(url)
        if url == COLLECTIONS_URL:
            return httpx.Response(200, json=[{"id": i} for i in pages_by_index] + [{"id": "not-an-index"}])
        index = request.url.path.removeprefix("/").removesuffix("-index")
        assert request.url.params["url"] == "jobs.ashbyhq.com/*"
        if index in fail:
            return httpx.Response(503)
        pages = pages_by_index[index]
        if request.url.params.get("showNumPages") == "true":
            return httpx.Response(200, json={"pages": len(pages), "pageSize": 5, "blocks": 2})
        assert request.url.params["output"] == "json" and request.url.params["fl"] == "url"
        return httpx.Response(200, text="\n".join(
            json.dumps({"url": f"https://jobs.ashbyhq.com/{slug}/{UUID}"})
            for slug in pages[int(request.url.params["page"])]))
    return handle, seen


def test_crawl_boards_unions_recent_crawls():
    handle, seen = crawl_handler({"CC-MAIN-2026-43": [["acme", "beta"]],
                                  "CC-MAIN-2026-38": [["beta"], ["gamma"]],
                                  "CC-MAIN-2026-33": [["old"]]})
    lines = []
    result = crawl_boards(cc_client(handle), crawls=2, sleep=lambda s: None, progress=lines.append)
    assert [b.slug for b in result.boards] == ["acme", "beta", "gamma"]   # oldest crawl not read
    assert result.indexes_read == ["CC-MAIN-2026-43", "CC-MAIN-2026-38"] and not result.errors
    assert lines == ["CC-MAIN-2026-43: 2 new companies (2 total)", "CC-MAIN-2026-38: 1 new companies (3 total)"]
    assert not any("2026-33" in url for url in seen)


def test_one_failed_crawl_does_not_lose_the_others():
    handle, _ = crawl_handler({"CC-MAIN-2026-43": [["acme"]], "CC-MAIN-2026-38": [["beta"]]},
                              fail={"CC-MAIN-2026-43"})
    result = crawl_boards(cc_client(handle), crawls=2, sleep=lambda s: None)
    assert [b.slug for b in result.boards] == ["beta"]
    assert result.indexes_read == ["CC-MAIN-2026-38"]
    assert len(result.errors) == 1 and result.errors[0].startswith("CC-MAIN-2026-43:")


def test_time_budget_stops_before_the_next_crawl_and_keeps_findings():
    handle, seen = crawl_handler({"CC-MAIN-2026-43": [["acme"]], "CC-MAIN-2026-38": [["beta"]],
                                  "CC-MAIN-2026-33": [["gamma"]]})
    ticks = iter([0, 0, 400, 400])  # start, before crawl 1, before crawl 2 (budget spent)
    result = crawl_boards(cc_client(handle), crawls=3, sleep=lambda s: None, budget_seconds=300,
                          clock=lambda: next(ticks))
    assert [b.slug for b in result.boards] == ["acme"] and result.indexes_read == ["CC-MAIN-2026-43"]
    assert result.errors == ["time budget (300 s) spent; skipped CC-MAIN-2026-38, CC-MAIN-2026-33"]
    assert not any("2026-38" in url or "2026-33" in url for url in seen)


def test_skip_reads_only_new_crawls():
    handle, seen = crawl_handler({"CC-MAIN-2026-43": [["new"]], "CC-MAIN-2026-38": [["old"]]})
    lines = []
    result = crawl_boards(cc_client(handle), crawls=2, sleep=lambda s: None, skip=["CC-MAIN-2026-38"])
    assert [b.slug for b in result.boards] == ["new"] and not any("2026-38" in url for url in seen)
    result = crawl_boards(cc_client(handle), crawls=2, sleep=lambda s: None, progress=lines.append,
                          skip=["CC-MAIN-2026-43", "CC-MAIN-2026-38"])
    assert result.boards == [] and not result.errors
    assert lines == ["all of the latest 2 crawls were already read"]


def test_crawl_boards_reports_when_nothing_is_reachable():
    result = crawl_boards(cc_client(lambda r: httpx.Response(503)), crawls=1, sleep=lambda s: None)
    assert result.boards == [] and "kept failing" in result.errors[0]
    with pytest.raises(ValueError):
        crawl_boards(cc_client(lambda r: httpx.Response(200)), "lever")       # Lever blocks the crawler
    with pytest.raises(ValueError):
        crawl_boards(cc_client(lambda r: httpx.Response(200)), crawls=0)


# --- Caches ---


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


def a_posting(**kw):
    values = dict(source="ashby", company="acme", posting_id=UUID, title="AI Engineer",
                  url=f"https://jobs.ashbyhq.com/acme/{UUID}", locations=("New York",), countries=("United States",))
    values.update(kw)
    return Posting(**values)


def test_company_list_cache_ages_out_but_stale_is_available(tmp_path):
    clock = Clock()
    cache = JobCache(tmp_path, now=clock)
    assert cache.load_companies("ashby") is None
    cache.save_companies("ashby", [CompanyBoard("ashby", "b"), CompanyBoard("ashby", "a")], {"indexes_read": ["x"]})
    boards, saved_at, details = cache.load_companies("ashby")
    assert [b.slug for b in boards] == ["a", "b"] and saved_at == clock.t and details == {"indexes_read": ["x"]}
    clock.t += 31 * 86400
    assert cache.load_companies("ashby") is None                          # too old to use by default
    assert cache.load_companies("ashby", max_age_days=None)[0][0].slug == "a"  # fallback when a refresh fails


def test_board_cache_round_trip_and_expiry(tmp_path):
    clock = Clock()
    cache = JobCache(tmp_path, now=clock)
    board = CompanyBoard("ashby", "acme")
    assert cache.save_board(BoardResult(board, postings=[a_posting()], skipped=2))
    loaded = cache.load_board(board, max_age_hours=24)
    assert loaded.postings == [a_posting()] and loaded.skipped == 2 and loaded.error is None
    clock.t += 25 * 3600
    assert cache.load_board(board, max_age_hours=24) is None


def test_only_missing_boards_are_cached_as_failures(tmp_path):
    cache = JobCache(tmp_path, now=Clock())
    gone, flaky = CompanyBoard("ashby", "gone"), CompanyBoard("ashby", "flaky")
    assert cache.save_board(BoardResult(gone, error="No public job board with that name (HTTP 404)."))
    assert not cache.save_board(BoardResult(flaky, error="The job board API timed out."))
    assert cache.load_board(gone, 24).error.endswith("(HTTP 404).")
    assert cache.load_board(flaky, 24) is None


@pytest.mark.parametrize("content", ["not json", "[]", '{"format": 99}',
                                     '{"format": 1, "saved_at": 1000000, "board": "ashby:acme", '
                                     '"postings": [{"title": "x", "evil": 1}]}',
                                     '{"format": 1, "saved_at": 1000000, "board": "ashby:other", "postings": []}'])
def test_corrupt_or_foreign_cache_files_are_misses(tmp_path, content):
    path = tmp_path / "boards" / "ashby-acme.json"
    path.parent.mkdir(parents=True)
    path.write_text(content)
    assert JobCache(tmp_path, now=Clock()).load_board(CompanyBoard("ashby", "acme"), 24) is None


def test_fetch_boards_cached_fetches_only_misses_and_keeps_order(tmp_path):
    cache = JobCache(tmp_path, now=Clock())
    cached_board, new_board = CompanyBoard("ashby", "cached"), CompanyBoard("ashby", "new")
    cache.save_board(BoardResult(cached_board, postings=[a_posting(company="cached")]))
    requested = []

    def handle(request):
        requested.append(request.url.path)
        return httpx.Response(200, json={"jobs": [{"id": UUID, "title": "ML Engineer"}]})

    client = httpx.Client(transport=httpx.MockTransport(handle))
    results, hits = fetch_boards_cached([cached_board, new_board], cache, client)
    assert hits == 1 and requested == ["/posting-api/job-board/new"]
    assert [r.board for r in results] == [cached_board, new_board]
    assert results[1].postings[0].title == "ML Engineer"
    _, hits = fetch_boards_cached([cached_board, new_board], cache, client)   # now both cached
    assert hits == 2 and len(requested) == 1
    _, hits = fetch_boards_cached([new_board], cache, client, max_age_hours=0)  # 0 disables the cache
    assert hits == 0 and len(requested) == 2


# --- Countries ---


def test_ashby_countries_come_from_structured_addresses():
    item = {"id": UUID, "title": "AI Engineer", "location": "New York City Office", "workplaceType": "Hybrid",
            "isRemote": True,  # seen live on Hybrid jobs: workplaceType must win
            "address": {"postalAddress": {"addressCountry": "USA", "addressLocality": "New York"}},
            "secondaryLocations": [
                {"location": "London", "address": {"postalAddress": {"addressCountry": "United Kingdom"}}},
                {"location": "Seattle", "address": {"postalAddress": {"addressCountry": "United States"}}},
                {"location": "Bad", "address": "not a dict"}, "plain string"]}
    posting = normalize(CompanyBoard("ashby", "acme"), {"jobs": [item]}).postings[0]
    assert posting.countries == ("United States", "United Kingdom")
    assert posting.workplace == "hybrid"
    assert posting.locations == ("New York City Office", "London", "Seattle", "Bad", "plain string")


@pytest.mark.parametrize("raw, name", [("USA", "United States"), ("United States of America", "United States"),
                                       ("u.s.", "United States"), ("UK", "United Kingdom"), ("Canada", "Canada"),
                                       ("", None), (None, None), (5, None)])
def test_normalize_country(raw, name):
    assert normalize_country(raw) == name


@pytest.mark.parametrize("locations, countries, expected", [
    # Cases a text-only "remote" filter let through in the live Ashby sample (November 17, 2026).
    (("Toronto",), (), {"Canada"}),
    (("London",), (), {"United Kingdom"}),
    (("Remote - UK",), (), {"United Kingdom"}),
    (("Europe; Israel (remote)",), (), {"Europe", "Israel"}),
    (("Remote – USA",), (), {"United States"}),
    (("New York, NY",), (), {"United States"}),
    (("Remote US",), (), {"United States"}),
    (("Albuquerque, New Mexico",), (), set()),          # not Mexico
    (("Remote",), (), set()),                           # unknown
    (("Cambridge; Remote",), ("United Kingdom",), {"United Kingdom"}),  # structured data decides
    (("Focus on us",), (), set()),                      # lowercase "us" is a word, not a country
])
def test_posting_countries(locations, countries, expected):
    assert posting_countries(a_posting(locations=locations, countries=countries)) == expected


def test_country_filter_drops_remote_abroad_keeps_unknown():
    jobs = [a_posting(posting_id="1", title="AI Engineer A", locations=("Remote - UK",), countries=(),
                      workplace="remote"),
            a_posting(posting_id="2", title="AI Engineer B", locations=("Toronto",), countries=("Canada",),
                      workplace="remote"),
            a_posting(posting_id="3", title="AI Engineer C", locations=("New York City Office",)),
            a_posting(posting_id="4", title="AI Engineer D", locations=("Remote",), countries=(), workplace="remote"),
            a_posting(posting_id="5", title="AI Engineer E", locations=("London", "Remote - United States"),
                      countries=("United Kingdom",))]
    titles = sorted(m.posting.title for m in rank(jobs, {"Python"}, "ai engineer", country="USA"))
    assert titles == ["AI Engineer C", "AI Engineer D", "AI Engineer E"]
    assert len(rank(jobs, {"Python"}, "ai engineer")) == 5              # no country: unchanged
    row = rank(jobs, {"Python"}, "ai engineer", country="united states")[0].as_dict()
    assert "countries" in row
