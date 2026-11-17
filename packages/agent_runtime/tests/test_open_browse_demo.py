"""Offline tests for scripts/e2b_open_browse_demo.py grading (W1X-F03)."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "e2b_open_browse_demo.py"
spec = importlib.util.spec_from_file_location("e2b_open_browse_demo", SCRIPT)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

START = "https://en.wikipedia.org/wiki/Main_Page"
ARTICLE = "https://en.wikipedia.org/wiki/Boston_Common"
SITE = "https://www.boston.gov/"
TYPE = {"tool": "type_text", "args": {"target_id": 3, "text": "Boston Common", "submit": True}}
NAV = {"tool": "navigate", "args": {"url": SITE}}
FINISH = {"tool": "finish", "args": {"answer": "boston.gov"}}


def test_search_then_named_site_passes():
    assert demo.grade("boston.gov", SITE, [START, ARTICLE, SITE], [TYPE, NAV, FINISH])[0]


@pytest.mark.parametrize("answer, final, visited, steps", [
    ("boston.gov", SITE, [START, ARTICLE, SITE], [NAV, FINISH]),                        # never typed
    ("boston.gov", SITE, [START, ARTICLE, SITE],
     [{"tool": "type_text", "args": {**TYPE["args"], "submit": False}}, NAV]),           # typed, not submitted
    ("boston.gov", SITE, [START, ARTICLE, SITE],
     [TYPE, {"tool": "click_link", "args": {"target_id": 9}}]),                         # never navigated
    ("boston.gov", SITE, [START, SITE], [TYPE, NAV]),                                   # search missed the article
    ("boston.gov", SITE, [START, SITE, ARTICLE], [TYPE, NAV]),                          # site before article only
    ("boston.gov", ARTICLE, [START, ARTICLE], [TYPE, NAV]),                             # never reached the site
    ("City of Boston", SITE, [START, ARTICLE, SITE], [TYPE, NAV]),                      # answer lacks domain
    (None, SITE, [START, ARTICLE, SITE], [TYPE, NAV]),
])
def test_grade_fails_on_any_missing_evidence(answer, final, visited, steps):
    assert not demo.grade(answer, final, visited, steps)[0]


@pytest.mark.parametrize("url, expected", [
    (ARTICLE, True), ("https://en.wikipedia.org/wiki/Boston%5FCommon", True),
    ("https://en.wikipedia.org/wiki/Boston_Common_(disambiguation)", False),
    ("https://de.wikipedia.org/wiki/Boston_Common", False), (None, False),
])
def test_article_match_is_exact(url, expected):
    assert demo.on_article(url) is expected
