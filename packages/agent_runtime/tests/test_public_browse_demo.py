"""Offline tests for scripts/e2b_public_browse_demo.py grading."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "e2b_public_browse_demo.py"
spec = importlib.util.spec_from_file_location("e2b_public_browse_demo", SCRIPT)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

START = "https://en.wikipedia.org/wiki/Boston"
SITE = "https://www.boston.gov/"


def test_click_to_boston_gov_with_named_answer_passes():
    assert demo.grade("boston.gov", SITE, [START, SITE], ["scroll", "click_link", "finish"])[0]


@pytest.mark.parametrize("answer, final, visited, tools", [
    ("boston.gov", SITE, [START, SITE], ["scroll", "finish"]),               # never clicked
    ("boston.gov", START, [START], ["click_link", "finish"]),                # stayed on Wikipedia
    ("boston.gov", "https://evilboston.gov.example/", [START], ["click_link"]),  # look-alike host
    ("City of Boston", SITE, [START, SITE], ["click_link", "finish"]),       # answer lacks the domain
    (None, SITE, [START, SITE], ["click_link"]),                             # no answer
])
def test_grade_fails_on_any_missing_evidence(answer, final, visited, tools):
    assert not demo.grade(answer, final, visited, tools)[0]


@pytest.mark.parametrize("url, expected", [
    ("https://www.boston.gov/", True), ("https://boston.gov/x", True),
    ("https://notboston.gov/", False), ("https://boston.gov.evil.com/", False), (None, False),
])
def test_target_host_match_is_exact_suffix(url, expected):
    assert demo.on_target(url) is expected
