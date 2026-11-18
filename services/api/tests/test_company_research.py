"""Company researcher: public inputs only, untrusted answers, host-verified quotes. No network."""
import json
import socket
import sys
from types import SimpleNamespace

import pytest

from crescendo_api import company_research as cr

JOB = {"source": "ashby", "posting_id": "x", "company": "Fictional Co", "title": "AI Engineer",
       "url": "https://jobs.ashbyhq.com/fictional/x", "description": "We build a profiler. " * 300,
       "company_notes": "PRIVATE-NOTE"}
PAGE = "<html><script>var hidden = 'Our profiler shows';</script><p>Our profiler shows developers\n where their code spends time.</p></html>"
FACT = {"topic": "product", "claim": "Builds a profiler.",
        "quote": "Our profiler shows developers where their code spends time.", "url": "https://fictional.example/about"}


def public_dns(monkeypatch, address="93.184.216.34"):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(0, 0, 0, "", (address, 443))])


def test_findings_are_the_last_json_object_and_bad_facts_are_dropped():
    content = ('[snippets] {"facts": "not yet"} more text ```json\n'
               + json.dumps({"facts": [FACT, {"claim": "no quote", "url": "https://a.example/b"}],
                             "open_questions": ["Team size?"]}) + "\n```")
    findings = cr.parse_findings(content)
    assert [f.claim for f in findings.facts] == ["Builds a profiler."]
    assert findings.open_questions == ["Team size?"]
    with pytest.raises(cr.ResearchUnavailable, match="no usable findings"):
        cr.parse_findings("I could not find anything.")


@pytest.mark.parametrize("url", ["http://fictional.example/", "https://user:pw@fictional.example/",
                                 "https://fictional.example:8443/", "file:///etc/passwd"])
def test_only_default_port_https_without_credentials(monkeypatch, url):
    public_dns(monkeypatch)
    with pytest.raises(cr.FetchRefused):
        cr.check_public_url(url)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1", "fd00::1", "192.168.1.1"])
def test_private_and_reserved_addresses_are_refused(monkeypatch, address):
    public_dns(monkeypatch, address)
    with pytest.raises(cr.FetchRefused, match="private or reserved"):
        cr.check_public_url("https://fictional.example/about")


class FakeResponse:
    def __init__(self, status=200, body=b"", headers=None):
        self.status_code, self.body = status, body
        self.headers = {"content-type": "text/html; charset=utf-8", **(headers or {})}
        self.encoding = "utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_bytes(self):
        for start in range(0, len(self.body), 1000):
            yield self.body[start:start + 1000]


class FakeClient:
    def __init__(self, routes):
        self.routes, self.seen = routes, []

    def stream(self, method, url, headers=None):
        self.seen.append(url)
        return self.routes[url]


def test_redirects_are_rechecked_and_page_text_excludes_scripts(monkeypatch):
    public_dns(monkeypatch)
    client = FakeClient({"https://fictional.example/": FakeResponse(301, headers={"location": "/about"}),
                         "https://fictional.example/about": FakeResponse(body=PAGE.encode())})
    text = cr.fetch_page_text("https://fictional.example/", client)
    assert client.seen == ["https://fictional.example/", "https://fictional.example/about"]
    assert "hidden" not in text and cr.comparable(FACT["quote"]) in cr.comparable(text)

    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(0, 0, 0, "", (
        "127.0.0.1" if host == "internal.example" else "93.184.216.34", 443))])
    client = FakeClient({"https://fictional.example/": FakeResponse(302, headers={"location": "https://internal.example/admin"})})
    with pytest.raises(cr.FetchRefused, match="private"):
        cr.fetch_page_text("https://fictional.example/", client)
    assert client.seen == ["https://fictional.example/"]  # never requested the private host


def test_size_type_and_status_bounds(monkeypatch):
    public_dns(monkeypatch)
    url = "https://fictional.example/x"
    for response, reason in [(FakeResponse(body=b"a" * (cr.FETCH_BYTES + 10)), "too large"),
                             (FakeResponse(body=b"%PDF", headers={"content-type": "application/pdf"}), "not HTML"),
                             (FakeResponse(404), "HTTP 404")]:
        with pytest.raises(cr.FetchRefused, match=reason):
            cr.fetch_page_text(url, FakeClient({url: response}))


def test_only_facts_quoted_on_their_page_are_kept():
    curly = {**FACT, "quote": "Our profiler shows developers where their code spends time—fast.",
             "url": "https://fictional.example/curly"}
    pages = {FACT["url"]: cr.visible_text(PAGE), curly["url"]: "Our profiler shows developers where their code spends time-fast.",
             "https://fictional.example/missing": "Unrelated text.",
             "https://fictional.example/down": cr.FetchRefused("The page returned HTTP 500.")}

    def fetch(url):
        page = pages[url]
        if isinstance(page, Exception):
            raise page
        return page

    facts = [cr.Fact(**FACT), cr.Fact(**curly), cr.Fact(**{**FACT, "quote": "We invented time travel.", "url": "https://fictional.example/missing"}),
             cr.Fact(**{**FACT, "quote": "Another quote here.", "url": "https://fictional.example/down"})]
    kept, excluded = cr.verify_facts(facts, fetch)
    assert [k["url"] for k in kept] == [FACT["url"], curly["url"]]
    assert {e["url"]: e["reason"] for e in excluded} == {
        "https://fictional.example/missing": "The quote was not found on the cited page.",
        "https://fictional.example/down": "The page returned HTTP 500."}


@pytest.fixture
def groq(monkeypatch):
    calls, state = [], {"content": json.dumps({"facts": [FACT]}), "error": None}

    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def create(self, **kwargs):
            calls.append(kwargs)
            if state["error"]:
                raise state["error"]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=state["content"]))])

    monkeypatch.setitem(sys.modules, "groq", SimpleNamespace(Groq=Client))
    return calls, state


def test_researcher_sees_only_public_posting_facts_and_uses_browser_search(groq):
    calls, _ = groq
    result = cr.research_company({**JOB, "resume": "PRIVATE-RESUME"}, "fake-key", "openai/gpt-oss-120b",
                                 fetch=lambda url: cr.visible_text(PAGE))
    request = calls[0]
    assert request["tools"] == [{"type": "browser_search"}] and request["tool_choice"] == "required"
    assert "response_format" not in request  # browser search can't use structured outputs
    sent = json.loads(request["messages"][1]["content"])
    assert set(sent) == {"company", "title", "posting_url", "posting_excerpt"}
    assert len(sent["posting_excerpt"]) == 3000
    assert "PRIVATE" not in request["messages"][1]["content"]
    assert result["status"] == "done" and result["facts"][0]["quote"] == FACT["quote"]
    assert cr.research_text({"company_research": result}).startswith("[1] Our profiler")


def test_research_provider_failure_is_safe(groq):
    _, state = groq
    error = type("RateLimitError", (Exception,), {})("PRIVATE-BODY")
    error.status_code, error.response = 429, SimpleNamespace(headers={})
    state["error"] = error
    with pytest.raises(cr.ResearchUnavailable, match="retry this company research") as caught:
        cr.research_company(JOB, "fake-key", "openai/gpt-oss-120b", fetch=lambda url: "")
    assert "PRIVATE" not in str(caught.value)
