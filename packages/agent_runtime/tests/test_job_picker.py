"""Offline tests for the job picker (JOB-F03)."""
import importlib.util
import io
import json
from pathlib import Path

import pytest

from crescendo_agent.job_picker import (PickError, PostingRef, candidates, clean, format_row,
                                        parse_choice, posting_ref, selection)

SCRIPT = Path(__file__).parents[3] / "scripts" / "pick_jobs.py"
spec = importlib.util.spec_from_file_location("pick_jobs", SCRIPT)
pick_jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pick_jobs)

UUID = "0f8fad5b-d9cb-469f-a165-70867728950e"
GREENHOUSE = "https://job-boards.greenhouse.io/acme/jobs/1234567"
LEVER = f"https://jobs.lever.co/beta/{UUID}"
ASHBY = f"https://jobs.ashbyhq.com/gamma/{UUID}"


def row(title, url, score=80, **extra):
    return {"score": score, "title": title, "company": "Acme", "url": url,
            "locations": ["New York, NY"], "workplace": "hybrid", "compensation": "$150k",
            "matched_skills": ["Python"], "missing_skills": ["Go"], **extra}


RANKED = {"search": "applied ai engineer",
          "results": [row("AI Engineer", GREENHOUSE), row("ML Engineer", LEVER),
                      row("Applied AI", ASHBY), row("Bad link", "https://evil.example/x")]}


# --- posting_ref: the board and ID later steps trust ---

@pytest.mark.parametrize("url, expected", [
    (GREENHOUSE, PostingRef("greenhouse", "acme", "1234567")),
    (LEVER, PostingRef("lever", "beta", UUID)),
    (ASHBY, PostingRef("ashby", "gamma", UUID)),
])
def test_known_ats_urls_give_board_and_id(url, expected):
    assert posting_ref(url) == expected
    assert posting_ref(url).url == url


@pytest.mark.parametrize("url", [
    "http://job-boards.greenhouse.io/acme/jobs/1234567",          # not https
    "https://job-boards.greenhouse.io/acme/jobs/12a",             # greenhouse IDs are digits
    "https://job-boards.greenhouse.io/acme/jobs/1234567?gh_src=x",  # query
    "https://job-boards.greenhouse.io/acme/jobs/1234567/",        # not the canonical form
    f"https://jobs.lever.co/beta/{UUID}#apply",                   # fragment
    "https://jobs.lever.co/beta/1234567",                         # lever IDs are UUIDs
    f"https://jobs.ashbyhq.com.evil.example/gamma/{UUID}",        # look-alike host
    f"https://user@jobs.ashbyhq.com/gamma/{UUID}",                # credentials
    f"https://jobs.ashbyhq.com:8443/gamma/{UUID}",                # port
    f"https://jobs.ashbyhq.com/../gamma/{UUID}",                  # bad slug
    f"https://jobs.ashbyhq.com/gamma/{UUID}/application",         # extra path
    "javascript:alert(1)", "", None, 42,
])
def test_anything_else_is_refused(url):
    assert posting_ref(url) is None


# --- clean: untrusted text reaching the terminal ---

def test_clean_removes_terminal_escapes_and_bidi_controls():
    assert clean("AI\x1b[31m Engineer‮\n") == "AI [31m Engineer"


def test_clean_bounds_length():
    assert clean("x" * 500, limit=10) == "x" * 9 + "…"


def test_clean_handles_none_and_numbers():
    assert clean(None) == "" and clean(7) == "7"


# --- candidates ---

def test_candidates_keep_rank_order_and_mark_bad_links():
    rows = candidates(RANKED)
    assert [r.rank for r in rows] == [1, 2, 3, 4]
    assert [r.ref is not None for r in rows] == [True, True, True, False]
    assert rows[0].where == "New York, NY, hybrid"


def test_candidates_survive_malformed_rows():
    rows = candidates({"results": ["junk", {"title": None, "score": "high", "locations": "NYC",
                                            "matched_skills": "Python", "url": GREENHOUSE}]})
    assert len(rows) == 1
    assert rows[0].title == "(untitled)" and rows[0].score == 0
    assert rows[0].where == "" and rows[0].have == ()


def test_candidates_reject_files_without_results():
    with pytest.raises(PickError):
        candidates({"search": "x"})
    with pytest.raises(PickError):
        candidates(["not", "a", "dict"])


def test_bad_link_row_is_shown_as_not_pickable():
    assert "not pickable" in format_row(candidates(RANKED)[3])


# --- parse_choice ---

@pytest.mark.parametrize("text, ranks", [
    ("1 3", [1, 3]), ("2,1", [2, 1]), (" 3 ,  2 ", [3, 2]), ("", []), ("  \n", []),
])
def test_valid_choices(text, ranks):
    assert [r.rank for r in parse_choice(text, candidates(RANKED))] == ranks


@pytest.mark.parametrize("text, phrase", [
    ("1 x", "not a number"), ("-1", "not a number"), ("9", "not in the list"),
    ("1 1", "picked twice"), ("4", "failed checks"), ("1.5", "not a number"),
])
def test_invalid_choices_explain_why(text, phrase):
    with pytest.raises(PickError, match=phrase):
        parse_choice(text, candidates(RANKED))


def test_at_most_three_picks():
    rows = candidates({"results": [row(f"Job {i}", f"https://job-boards.greenhouse.io/acme/jobs/{i}")
                                   for i in range(1, 6)]})
    assert len(parse_choice("1 2 3", rows)) == 3
    with pytest.raises(PickError, match="at most 3"):
        parse_choice("1 2 3 4", rows)


def test_only_shown_rows_can_be_picked():
    with pytest.raises(PickError, match="not in the list"):
        parse_choice("3", candidates(RANKED)[:2])


def test_selection_has_what_later_steps_need():
    picked = parse_choice("3", candidates(RANKED))
    result = selection(RANKED, "jobs-ranked-x.json", picked, "2026-11-17T23:00:00+00:00")
    job = result["jobs"][0]
    assert result["search"] == "applied ai engineer"
    assert (job["source"], job["board"], job["posting_id"], job["url"]) == ("ashby", "gamma", UUID, ASHBY)


# --- the script ---

@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(pick_jobs, "ARTIFACTS", tmp_path / ".demo-artifacts")
    (tmp_path / ".demo-artifacts").mkdir()
    (tmp_path / ".demo-artifacts" / "jobs-ranked-a.json").write_text(json.dumps(RANKED))
    return tmp_path / ".demo-artifacts"


def saved(directory):
    files = list(directory.glob("jobs-picked-*.json"))
    return json.loads(files[0].read_text()) if files else None


def test_script_saves_a_pick_from_the_newest_list(workdir):
    assert pick_jobs.main(["--pick", "1 2"]) == 0
    assert [job["title"] for job in saved(workdir)["jobs"]] == ["AI Engineer", "ML Engineer"]


def test_script_interactive_retries_then_saves(workdir, capsys):
    assert pick_jobs.main([], stdin=io.StringIO("1 2 3 4 5\n9\n2\n")) == 0
    assert [job["rank"] for job in saved(workdir)["jobs"]] == [2]
    assert "at most 3" in capsys.readouterr().err


def test_script_gives_up_after_three_bad_answers(workdir):
    assert pick_jobs.main([], stdin=io.StringIO("x\ny\nz\n")) == 2
    assert saved(workdir) is None


def test_script_cancel_saves_nothing(workdir):
    assert pick_jobs.main([], stdin=io.StringIO("")) == 1
    assert saved(workdir) is None


def test_script_bad_pick_flag_fails_without_prompt(workdir):
    assert pick_jobs.main(["--pick", "4"], stdin=io.StringIO("1\n")) == 2
    assert saved(workdir) is None


def test_script_without_ranked_list(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pick_jobs, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(pick_jobs, "newest_ranked", lambda: None)
    assert pick_jobs.main(["--pick", "1"]) == 2
    assert "find_jobs.py" in capsys.readouterr().err
