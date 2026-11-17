"""Public-web mode in the desktop adapter (W1X-F02). Fakes replace Chrome and E2B."""
from unittest.mock import Mock

import pytest

from crescendo_agent.e2b_desktop import E2BDesktop, network_config, open_e2b_desktop
from crescendo_security.policy import PRIVATE_NETWORKS, TaskGrant

PUBLIC = TaskGrant("public", frozenset({"screenshot", "scroll", "click", "read_visible_links", "finish"}),
                   frozenset(), public_web=True)
ALLOWLIST = TaskGrant("list", frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))


def test_network_config_per_mode():
    assert network_config(ALLOWLIST) == {"deny_out": ["0.0.0.0/0"], "allow_out": ["en.wikipedia.org"],
                                         "allow_public_traffic": False}
    public = network_config(PUBLIC)
    assert public == {"deny_out": list(PRIVATE_NETWORKS), "allow_public_traffic": False}
    assert "allow_out" not in public  # no allowlist: public destinations are open


def test_desktop_is_created_with_the_grants_network_config():
    factory = Mock()
    factory.create.return_value.commands.run.side_effect = RuntimeError("stop after create")
    with pytest.raises(RuntimeError), open_e2b_desktop(PUBLIC, sandbox_type=factory):
        pass
    assert factory.create.call_args.kwargs["network"] == network_config(PUBLIC)
    assert factory.create.call_args.kwargs["lifecycle"] == {"on_timeout": "kill"}
    factory.create.return_value.kill.assert_called_once_with()


@pytest.mark.parametrize("url, kind, allowed", [
    ("https://www.boston.gov/", "Document", True),
    ("https://cdn.example.net/site.css", "Stylesheet", True),
    ("https://www.boston.gov/logo.png", "Image", False),            # type rule unchanged
    ("https://10.0.0.1/", "Document", False),
    ("https://169.254.169.254/latest/meta-data/", "Document", False),
    ("https://localhost/", "Document", False),
    ("https://2130706433/", "Document", False),
    ("http://www.boston.gov/", "Document", False),
])
def test_public_mode_filter_checks_destination_not_tools(url, kind, allowed):
    # PUBLIC has no navigate tool, yet public pages must still load: the filter
    # judges destinations, not model tools.
    session = Mock()
    desktop = E2BDesktop(Mock(), session, PUBLIC)
    desktop._request_paused({"requestId": "r", "resourceType": kind,
                             "request": {"url": url, "method": "GET"}})
    expected = ("Fetch.continueRequest", {"requestId": "r"}) if allowed else (
        "Fetch.failRequest", {"requestId": "r", "errorReason": "BlockedByClient"})
    session.send.assert_called_with(*expected)


def test_model_navigate_needs_the_tool_but_host_start_page_does_not():
    page = Mock()
    page.url = "https://en.wikipedia.org/wiki/Boston"
    page.goto.return_value = None
    desktop = E2BDesktop(page, Mock(), PUBLIC)
    with pytest.raises(ValueError, match="not permitted"):
        desktop.navigate("https://en.wikipedia.org/wiki/Boston")  # no navigate tool granted
    page.goto.assert_not_called()
    desktop.open_start_page("https://en.wikipedia.org/wiki/Boston")
    page.goto.assert_called_once()
    assert desktop.visited == ["https://en.wikipedia.org/wiki/Boston"]


def test_open_browsing_navigate_loads_any_public_site_and_reports_it():
    # Decision 0005: with the navigate tool, the model may name a public site itself.
    page = Mock()
    page.url = "https://www.boston.gov/"
    page.goto.return_value = None
    granted = TaskGrant("o", PUBLIC.allowed_tools | {"navigate"}, frozenset(), public_web=True)
    desktop = E2BDesktop(page, Mock(), granted)
    assert desktop.navigate_and_report("https://www.boston.gov/") == "The tab now shows https://www.boston.gov/."
    assert desktop.visited == ["https://www.boston.gov/"]
    with pytest.raises(ValueError, match="IP addresses"):
        desktop.navigate_and_report("https://169.254.169.254/latest/")
    assert page.goto.call_count == 1


def test_a_model_url_that_fails_to_load_is_reported_not_raised():
    from playwright.sync_api import Error

    page = Mock()
    page.goto.side_effect = Error("net::ERR_NAME_NOT_RESOLVED at https://no-such-site.example/ secret")
    granted = TaskGrant("o", PUBLIC.allowed_tools | {"navigate"}, frozenset(), public_web=True)
    desktop = E2BDesktop(page, Mock(), granted)
    outcome = desktop.navigate_and_report("https://no-such-site.example/")
    assert outcome == "The page did not load (net::ERR_NAME_NOT_RESOLVED)."
    assert "secret" not in outcome and desktop.visited == []
    assert "did not load" in desktop.observe().text
    # Plain navigate keeps raising, so other callers still see real browser errors.
    with pytest.raises(Error):
        desktop.navigate("https://no-such-site.example/")


def test_start_page_still_checks_the_destination():
    page = Mock()
    desktop = E2BDesktop(page, Mock(), PUBLIC)
    with pytest.raises(ValueError, match="IP addresses"):
        desktop.open_start_page("https://10.0.0.1/")
    page.goto.assert_not_called()
