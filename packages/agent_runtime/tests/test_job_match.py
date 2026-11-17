"""Offline tests for JOB-F02: company discovery (HN), resume reading, and keyword ranking."""
from datetime import datetime, timezone
import json

import httpx
import pytest

from crescendo_agent.company_discovery import (HN_ITEM, HN_SEARCH, boards_in_text, hn_hiring_boards,
                                               read_boards_file)
from crescendo_agent.job_match import (SMOOTHING, age_days, company_label, extract_skills, rank,
                                       resume_skills, title_match, years_asked)
from crescendo_agent.job_sources import CompanyBoard, Posting
from crescendo_agent.resume import ResumeError, read_resume_text


def posting(title, description="", **kw):
    fields = dict(source="ashby", company="acme-ai", posting_id="x", url="https://jobs.ashbyhq.com/acme-ai/x")
    fields.update(kw)
    return Posting(title=title, description=description, **fields)


# --- Company discovery ---

def test_boards_in_text_keeps_only_ats_boards_once():
    text = ('Apply: <a href="https:&#x2F;&#x2F;jobs.ashbyhq.com&#x2F;Mastra&#x2F;123">x</a> or '
            "https://jobs.lever.co/curai/abc, https://job-boards.greenhouse.io/acme. Also "
            "https://boards.greenhouse.io/embed/job_app?for=x https://jobs.ashbyhq.com/mastra "
            "https://evil.example/jobs.lever.co/fake https://jobs.lever.co/../etc")
    assert boards_in_text(text) == [CompanyBoard("ashby", "mastra"), CompanyBoard("lever", "curai"),
                                    CompanyBoard("greenhouse", "acme")]


def test_read_boards_file(tmp_path):
    path = tmp_path / "boards.txt"
    path.write_text("# mine\nlever:palantir  # note\n\nashby:openai\nlever:palantir\n")
    assert read_boards_file(path) == [CompanyBoard("lever", "palantir"), CompanyBoard("ashby", "openai")]
    path.write_text("lever:palantir\nworkday:acme\n")
    with pytest.raises(ValueError, match=":2:"):
        read_boards_file(path)


def hn_client(search, items, status=200):
    def handle(request):
        url = str(request.url)
        if url == HN_SEARCH:
            return httpx.Response(status, json=search)
        story = url.rsplit("/", 1)[-1]
        return httpx.Response(200, json=items[story])
    return httpx.Client(transport=httpx.MockTransport(handle))


SEARCH = {"hits": [
    {"objectID": "3", "title": "Ask HN: Who is hiring? (November 2026)"},
    {"objectID": "2", "title": "Ask HN: Who wants to be hired? (November 2026)"},
    {"objectID": "1", "title": "Ask HN: Who is hiring? (October 2026)"},
    {"objectID": "x9", "title": "Ask HN: Who is hiring? (May 2026)"}]}
ITEMS = {"3": {"children": [{"text": "https://jobs.lever.co/curai"}, {"text": None}, "junk"]},
         "1": {"children": [{"text": "https://jobs.ashbyhq.com/mastra https://jobs.lever.co/curai"}]}}


def test_hn_reads_only_hiring_threads_newest_first():
    boards, labels, error = hn_hiring_boards(hn_client(SEARCH, ITEMS), months=3)
    assert error is None and labels == ["November 2026", "October 2026"]
    assert boards == [CompanyBoard("lever", "curai"), CompanyBoard("ashby", "mastra")]
    assert hn_hiring_boards(hn_client(SEARCH, ITEMS), months=1)[0] == [CompanyBoard("lever", "curai")]


def test_hn_failures_are_reported_not_raised():
    assert hn_hiring_boards(hn_client({}, {}, status=503), 1)[2] == "HN API answered HTTP 503."
    assert hn_hiring_boards(hn_client({"hits": []}, {}), 1)[2] == "No 'Who is hiring?' threads were found."

    def boom(request):
        raise httpx.ConnectError("down", request=request)
    assert "ConnectError" in hn_hiring_boards(httpx.Client(transport=httpx.MockTransport(boom)), 1)[2]
    with pytest.raises(ValueError):
        hn_hiring_boards(hn_client(SEARCH, ITEMS), months=0)


# --- Resume ---

def test_resume_text_and_errors(tmp_path):
    text = tmp_path / "r.md"
    text.write_text("  Python   and\n\nRAG  ")
    assert read_resume_text(text) == "Python and\n\nRAG"
    (tmp_path / "blank.txt").write_text("   ")
    for name, words in [("missing.pdf", "No file"), ("blank.txt", "No text found")]:
        with pytest.raises(ResumeError, match=words):
            read_resume_text(tmp_path / name)
    (tmp_path / "r.docx").write_bytes(b"x")
    with pytest.raises(ResumeError, match="Use a .pdf"):
        read_resume_text(tmp_path / "r.docx")
    (tmp_path / "bad.pdf").write_bytes(b"not a pdf")
    with pytest.raises(ResumeError, match="could not be read"):
        read_resume_text(tmp_path / "bad.pdf")


def test_resume_pdf(tmp_path):
    # A minimal one-page PDF with the text "Python RAG PyTorch".
    stream = b"BT /F1 12 Tf 72 720 Td (Python RAG PyTorch) Tj ET"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
               b"/Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length %d >>stream\n" % len(stream) + stream + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    pdf, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    pdf += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref
    path = tmp_path / "resume.pdf"
    path.write_bytes(pdf)
    assert read_resume_text(path) == "Python RAG PyTorch"


# --- Skills and scoring ---

@pytest.mark.parametrize("text, present, absent", [
    ("Python, Go, and Rust services", {"Python", "Go", "Rust"}, set()),
    ("Let's go to market fast", set(), {"Go"}),
    ("JavaScript developer", {"JavaScript"}, {"Java"}),
    ("retrieval-augmented generation with pgvector", {"RAG", "Vector databases"}, set()),
    ("insurance agents and user agents", set(), {"AI agents"}),
    ("building LLM agents and agentic workflows", {"AI agents", "LLMs"}, set()),
    ("Swift", {"Swift"}, set()), ("swift delivery", set(), {"Swift"}),
    ("C++ and C#", {"C++", "C#"}, set()),
    ("Python, FastAPI, Temporal, PostgreSQL", {"Temporal"}, set()),
    ("Temporal durable workflows", {"Temporal"}, set()),
    ("temporal patterns in time-series data", set(), {"Temporal"}),
    ("Join Stripe! We build payments infrastructure", set(), {"Payments integration"}),
    ("Stripe Connect payments", {"Payments integration"}, set()),
    ("SAST/DAST with Semgrep and OWASP ZAP", {"Application security"}, set()),
    ("Japanese (Native)", {"Japanese"}, set()), ("event-driven systems on Amazon Bedrock",
                                                 {"Event-driven architecture", "Amazon Bedrock"}, set()),
    ("React Native and Expo on iOS", {"React Native", "React", "iOS"}, set()),
    ("Bios and studios", set(), {"iOS"}),
])
def test_extract_skills(text, present, absent):
    found = extract_skills(text)
    assert present <= found and not (absent & found)


def test_resume_skills_add_implied_ones_only():
    assert resume_skills("RAG with PyTorch") == {"RAG", "LLMs", "Generative AI", "PyTorch", "Deep learning",
                                                 "Machine learning"}


@pytest.mark.parametrize("query, title, expected", [
    ("applied ai engineer", "Senior Applied AI Engineer", 1.0),
    ("applied ai engineer", "Machine Learning Engineer", 2 / 3),
    ("applied ai engineer", "AI Developer", 2 / 3),
    ("applied ai engineer", "Research Engineer", 1 / 3),
    ("the", "Anything", 0.0),
])
def test_title_match(query, title, expected):
    assert title_match(query, title) == pytest.approx(expected)


def test_years_asked():
    assert years_asked("You have 5+ years of professional experience and 3 years experience in Go") == 3
    assert years_asked("Founded 10 years ago. Great experience!") is None
    assert years_asked("2-4 years of industry experience") == 2


def test_rank_scores_filters_and_explains():
    have = {"Python", "RAG", "LLMs"}
    jobs = [
        posting("Applied AI Engineer", "Python, RAG, LLMs, Kubernetes. 4+ years of experience",
                published_at="2026-11-01T00:00:00Z"),
        posting("AI Engineer", "Python only"),
        posting("Accountant", "Python, RAG, LLMs"),                          # irrelevant title
        posting("Applied AI Engineer", "", locations=("Berlin",), workplace="onsite", company="other-co"),
    ]
    matches = rank(jobs, have, "applied ai engineer")
    # A partly matching title with a matched skill beats an exact title with no skills listed.
    assert [m.posting.title for m in matches] == ["Applied AI Engineer", "AI Engineer", "Applied AI Engineer"]
    best = matches[0]
    assert best.matched_skills == ("LLMs", "Python", "RAG") and best.missing_skills == ("Kubernetes",)
    assert best.skill_coverage == pytest.approx(3 / (4 + SMOOTHING))
    assert best.score == round(100 * (0.3 * 1.0 + 0.7 * 3 / 6)) and best.years_asked == 4
    assert matches[2].score == 30  # exact title, no skills listed
    row = best.as_dict()
    assert row["company"] == "Acme Ai" and row["url"].startswith("https://jobs.ashbyhq.com/")
    assert [m.posting.locations for m in rank(jobs, have, "applied ai engineer", location="berlin")] == [("Berlin",)]
    assert rank(jobs, have, "applied ai engineer", remote=True) == []
    with pytest.raises(ValueError):
        rank(jobs, have, "the")


def test_smoothing_prefers_more_evidence_at_the_same_match_rate():
    have = {"Python", "RAG", "LLMs", "Docker", "AWS", "React", "Kafka", "Redis"}
    few = posting("AI Engineer", "Python, RAG, LLMs, Docker, Rust")                         # 4 of 5
    many = posting("AI Engineer", "Python, RAG, LLMs, Docker, AWS, React, Kafka, Redis, "
                                  "Rust, Terraform", company="other-co")                                          # 8 of 10
    scores = {m.posting.description[:40]: m.score for m in rank([few, many], have, "ai engineer")}
    assert scores[many.description[:40]] > scores[few.description[:40]]


def test_company_label_and_age():
    assert company_label(posting("x", company="charge-robotics")) == "Charge Robotics"
    assert company_label(posting("x", company_name="Anthropic")) == "Anthropic"
    now = datetime(2026, 11, 17, tzinfo=timezone.utc)
    assert age_days("2026-11-07T12:00:00Z", now) == 9 and age_days(None) is None and age_days("bad") is None


def test_seniority_years_and_any_of_locations():
    from crescendo_agent.job_match import is_senior_title
    have = {"Python"}
    jobs = [posting("Senior AI Engineer", "Python", posting_id="1"),
            posting("AI Engineer", "Python. 5+ years of experience required", posting_id="2"),
            posting("AI Engineer II", "Python. 2+ years of experience", locations=("New York, NY",), posting_id="3"),
            posting("AI Engineer III", "Python", locations=("Remote - United States",), workplace="remote",
                    posting_id="4")]
    titles = lambda **kw: [m.posting.title for m in rank(jobs, have, "ai engineer", **kw)]
    assert "Senior AI Engineer" not in titles(no_senior=True)
    assert "AI Engineer" not in titles(max_years=3)          # asks 5
    assert "AI Engineer III" in titles(max_years=3)          # states no years: kept
    assert sorted(titles(location=["new york", "remote"])) == ["AI Engineer II", "AI Engineer III"]
    assert titles(location="new york") == ["AI Engineer II"]
    assert [is_senior_title(t) for t in ("Sr. Engineer", "Staff SWE", "Engineering Manager", "AI Engineer",
                                          "Leader-board dev")] == [True, True, True, False, False]


def test_same_role_in_many_cities_is_one_row():
    jobs = [posting("AI Engineer", "Python", locations=(city,), posting_id=str(i))
            for i, city in enumerate(["Spain", "Canada", "Spain", "Australia"])]
    jobs.append(posting("AI Engineer", "Python", company="other", posting_id="9"))
    rows = rank(jobs, {"Python"}, "ai engineer")
    assert len(rows) == 2
    acme = next(r for r in rows if r.posting.company == "acme-ai")
    assert acme.posting.locations == ("Spain", "Canada", "Australia") and acme.other_postings == 3
    assert acme.as_dict()["other_postings"] == 3
