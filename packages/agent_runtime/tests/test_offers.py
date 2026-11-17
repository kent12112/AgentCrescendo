"""Offline tests for the offer finder (JOB-F01): board/posting recognition and the finish check."""
import json
from unittest.mock import Mock

import pytest

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_agent.link_grounding import LINK_RECORDS
from crescendo_agent.offers import (Board, board_from_url, is_generic_label, offer_goal,
                                    offer_validator, parse_offer_answer, posting_company)
from crescendo_security.policy import TaskGrant

GH = "https://job-boards.greenhouse.io/acme"
LEVER_ID = "ac978161-6f46-4f6b-ad9e-a258e642751c"


@pytest.mark.parametrize("url, expected", [
    (GH, Board("greenhouse", "acme", GH)),
    ("https://boards.greenhouse.io/Acme/", Board("greenhouse", "acme", "https://boards.greenhouse.io/Acme/")),
    ("https://jobs.lever.co/palantir", Board("lever", "palantir", "https://jobs.lever.co/palantir")),
    ("http://jobs.lever.co/palantir", None),               # not https
    ("https://jobs.lever.co/palantir?team=x", None),       # filters are not boards yet
    ("https://jobs.ashbyhq.com/openai", None),             # needs page scripts
    ("https://job-boards.greenhouse.io/acme/jobs/1", None),  # a posting, not a board
    ("https://evil.example/acme", None),
])
def test_board_from_url(url, expected):
    assert board_from_url(url) == expected


@pytest.mark.parametrize("href, expected", [
    (GH + "/jobs/5183044008", ("greenhouse", "acme")),
    (GH + "/jobs/5183044008?gh_src=x", ("greenhouse", "acme")),
    (f"https://jobs.lever.co/palantir/{LEVER_ID}", ("lever", "palantir")),
    (f"https://jobs.lever.co/palantir/{LEVER_ID}/apply", None),
    (GH, None),
    (GH + "/jobs/abc", None),
    ("https://job-boards.greenhouse.io.evil.example/acme/jobs/1", None),
    (f"http://jobs.lever.co/palantir/{LEVER_ID}", None),
    ("javascript:alert(1)", None),
])
def test_posting_company(href, expected):
    assert posting_company(href) == expected


@pytest.mark.parametrize("label, generic", [
    ("APPLY", True), (" Apply now → ", True), ("View job", True),
    ("Backend Engineer, Payments", False), ("Apply Scientist", False)])
def test_generic_labels(label, generic):
    assert is_generic_label(label) is generic


def test_parse_accepts_well_formed_and_empty():
    assert parse_offer_answer('{"offers": [{"link_id": 3, "why": " Python backend "}]}') == [(3, "Python backend")]
    assert parse_offer_answer('{"offers": []}') == []


@pytest.mark.parametrize("answer, words", [
    ("Here are the jobs: 1, 2", "not JSON"),
    ('{"offers": [], "note": "x"}', "only an offers list"),
    ('[{"link_id": 1, "why": "x"}]', "only an offers list"),
    ('{"offers": [{"link_id": 1}]}', "exactly link_id and why"),
    ('{"offers": [{"link_id": 1, "why": "x", "url": "https://x"}]}', "exactly link_id and why"),
    ('{"offers": [{"link_id": "1", "why": "x"}]}', "positive integer"),
    ('{"offers": [{"link_id": true, "why": "x"}]}', "positive integer"),
    ('{"offers": [{"link_id": 0, "why": "x"}]}', "positive integer"),
    ('{"offers": [{"link_id": 1, "why": "x"}, {"link_id": 1, "why": "y"}]}', "twice"),
    ('{"offers": [{"link_id": 1, "why": "  "}]}', "nonblank line"),
    ('{"offers": [{"link_id": 1, "why": "a\\nb"}]}', "nonblank line"),
    (json.dumps({"offers": [{"link_id": 1, "why": "x" * 201}]}), "nonblank line"),
    (json.dumps({"offers": [{"link_id": i, "why": "x"} for i in range(1, 7)]}), "Too many"),
])
def test_parse_refuses_with_a_fixable_reason(answer, words):
    with pytest.raises(ValueError, match=words) as error:
        parse_offer_answer(answer)
    assert "Finish with only JSON" in str(error.value)


def record(link_id, label, href):
    return {"label": label, "href": href, "x": 100 + link_id, "y": 200}


class FakeDesktop:
    def __init__(self, records):
        self.records = records
        self.asked = []

    def link_records(self, ids):
        self.asked.append(list(ids))
        return {i: self.records[i] for i in ids if i in self.records}


BOARD = Board("greenhouse", "acme", GH)


def test_validator_builds_offers_from_browser_records_not_model_text():
    desktop = FakeDesktop({4: record(4, "Backend Engineer Remote, US", GH + "/jobs/77")})
    accepted = []
    validate = offer_validator(desktop, BOARD, accepted)
    assert validate('{"offers": [{"link_id": 4, "why": "Python and Postgres"}]}') is None
    assert accepted == [{"link_id": 4, "title": "Backend Engineer Remote, US", "url": GH + "/jobs/77",
                         "company": "acme", "platform": "greenhouse", "screen_point": [104, 200],
                         "why_untrusted": "Python and Postgres"}]


@pytest.mark.parametrize("records, words", [
    ({}, "not a link in the current visible_links"),
    ({4: record(4, "Careers home", GH)}, "not a job posting"),
    ({4: record(4, "Backend", "https://job-boards.greenhouse.io/other/jobs/7")}, "not a job posting"),
    ({4: record(4, "Backend", "https://jobs.lever.co/acme/" + LEVER_ID)}, "not a job posting"),
    ({4: record(4, "APPLY", GH + "/jobs/77")}, "not Apply"),
])
def test_validator_refuses_ids_that_are_not_postings_on_this_board(records, words):
    accepted = [{"stale": True}]
    validate = offer_validator(FakeDesktop(records), BOARD, accepted)
    reason = validate('{"offers": [{"link_id": 4, "why": "fits"}]}')
    assert reason is not None and words in reason
    assert accepted == []


def test_validator_passes_parse_errors_back_without_touching_the_page():
    desktop = FakeDesktop({})
    reason = offer_validator(desktop, BOARD, [])("Backend Engineer at Acme")
    assert "not JSON" in reason and desktop.asked == []


def test_validator_accepts_honest_empty_answer():
    accepted = []
    assert offer_validator(FakeDesktop({}), BOARD, accepted)('{"offers": []}') is None
    assert accepted == []


def test_goal_keeps_user_words_bounded():
    goal = offer_goal(BOARD, "remote Python backend role")
    assert "'remote Python backend role'" in goal and "link_id" in goal and "acme" in goal
    for bad in ("", "  ", "a\nb", "x" * 201, None):
        with pytest.raises(ValueError):
            offer_goal(BOARD, bad)


def test_link_records_only_reads_ids_in_the_current_snapshot():
    page, session = Mock(), Mock()
    page.url = GH
    grant = TaskGrant("offers", frozenset({"read_visible_links", "click"}), frozenset(), public_web=True)
    desktop = E2BDesktop(page, session, grant)
    snapshot = Mock()
    desktop._link_snapshot = snapshot
    desktop._visible_link_ids = {4, 5}
    snapshot.evaluate.return_value = [{"id": 4, "label": "Backend", "href": GH + "/jobs/7", "x": 1, "y": 2}]
    assert desktop.link_records([4, 9, "5", True]) == {4: {"label": "Backend", "href": GH + "/jobs/7", "x": 1, "y": 2}}
    snapshot.evaluate.assert_called_once_with(LINK_RECORDS, [4])
    snapshot.evaluate.reset_mock()
    assert desktop.link_records([9]) == {}
    snapshot.evaluate.assert_not_called()
    snapshot.evaluate.side_effect = RuntimeError("context destroyed")
    assert desktop.link_records([5]) == {}


# --- Loop integration: the real run_vision_agent with a fake board and a scripted model. ---

import importlib.util
from pathlib import Path

from crescendo_agent.e2b_desktop import PAGE_AREA
from crescendo_agent.vision_loop import run_vision_agent
from crescendo_security.policy import ToolCall

from test_click import Script, png

LOOP_GRANT = TaskGrant("offers", frozenset({"screenshot", "scroll", "click", "read_visible_links", "finish"}),
                       frozenset(), public_web=True)


class BoardDesktop:
    """One board screen: a navigation link (1), a posting title (2), and its Apply button (3)."""

    RECORDS = {1: record(1, "Life at Acme", "https://acme.example/life"),
               2: record(2, "Backend Engineer Remote, US", GH + "/jobs/77"),
               3: record(3, "APPLY", GH + "/jobs/77")}

    def capture_screen(self):
        return png(1024, 768)

    def click_area(self):
        return PAGE_AREA

    def visible_links(self):
        return [{"id": i, "label": r["label"]} for i, r in self.RECORDS.items()]

    def link_records(self, ids):
        return {i: self.RECORDS[i] for i in ids if i in self.RECORDS}


def finish(offers):
    return ToolCall("finish", {"answer": json.dumps({"offers": offers})})


def test_loop_refuses_a_bad_citation_then_accepts_the_corrected_one():
    accepted = []
    model = Script([finish([{"link_id": 3, "why": "apply button"}]),
                    finish([{"link_id": 2, "why": "backend, remote"}])])
    result = run_vision_agent("find", LOOP_GRANT, BoardDesktop(), model, link_grounding=True,
                              finish_validator=offer_validator(BoardDesktop(), BOARD, accepted))
    assert result.status == "finished"
    assert [d.reason for _, d in result.denied] == [
        "link_id 3 ('APPLY') is not a job posting on this company's board. "
        "Cite the posting's title link, not Apply or navigation links."]
    # The model saw the refusal before its second answer.
    assert any(e.kind == "denied" and "not a job posting" in e.text for e in model.seen[1][1])
    assert [(o["title"], o["url"]) for o in accepted] == [("Backend Engineer Remote, US", GH + "/jobs/77")]


def test_loop_never_accepts_an_invented_id():
    accepted = []
    model = Script([finish([{"link_id": 99, "why": "made up"}])] * 2)
    result = run_vision_agent("find", LOOP_GRANT, BoardDesktop(), model, link_grounding=True, max_steps=2,
                              finish_validator=offer_validator(BoardDesktop(), BOARD, accepted))
    assert result.status == "step_limit" and accepted == []


SCRIPT = Path(__file__).parents[3] / "scripts" / "e2b_offer_finder_demo.py"
_spec = importlib.util.spec_from_file_location("e2b_offer_finder_demo", SCRIPT)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


def test_demo_grade():
    assert demo.grade("finished", [{"title": "x"}])[0]
    assert demo.grade("finished", [])[1].startswith("NO MATCH")
    for status in ("step_limit", "deadline", "rate_limited", "model_timeout"):
        assert not demo.grade(status, [{"title": "x"}])[0]
