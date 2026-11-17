"""Offline tests for scripts/e2b_network_browser_check.py. A fake page replaces Chrome."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "e2b_network_browser_check.py"


def load_script():
    spec = importlib.util.spec_from_file_location("e2b_network_browser_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load_script()


def good_evidence():
    subresources = {url: "blocked_by_filter" for url in check.MUST_NOT_LOAD}
    subresources[check.ALLOWED_CSS] = "loaded"
    return {
        "subresources": subresources,
        "meta_refresh": {"blocked": True, "final_url": "about:blank"},
        "redirect": {"blocked_hosts": ["en.wiktionary.org"], "final_url": "about:blank", "status": None},
    }


def test_expected_browser_boundary_passes():
    passed, lines = check.judge(good_evidence())
    assert passed and all(line.startswith("PASS") for line in lines)


@pytest.mark.parametrize("url", list(check.MUST_NOT_LOAD))
def test_any_loaded_forbidden_subresource_fails(url):
    evidence = good_evidence()
    evidence["subresources"][url] = "loaded"
    passed, lines = check.judge(evidence)
    assert not passed and f"FAIL: {url} did not load (loaded)" in lines


def test_filter_items_must_be_caught_by_our_filter_not_just_fail():
    # Failing elsewhere would mean our filter never saw the request.
    evidence = good_evidence()
    evidence["subresources"]["https://example.com/blocked.png"] = "failed_elsewhere"
    assert not check.judge(evidence)[0]
    evidence = good_evidence()
    evidence["subresources"]["https://10.0.0.1/private.png"] = "failed_elsewhere"
    assert check.judge(evidence)[0]


def test_allowed_stylesheet_must_load():
    evidence = good_evidence()
    evidence["subresources"][check.ALLOWED_CSS] = "blocked_by_filter"
    assert not check.judge(evidence)[0]


@pytest.mark.parametrize("refresh", [{"blocked": False, "final_url": "about:blank"},
                                     {"blocked": True, "final_url": "https://example.com/refresh"}])
def test_meta_refresh_must_be_blocked_and_page_unchanged(refresh):
    evidence = good_evidence()
    evidence["meta_refresh"] = refresh
    assert not check.judge(evidence)[0]


@pytest.mark.parametrize("final_url", ["about:blank", "chrome-error://chromewebdata/",
                                       "https://en.wikipedia.org/wiki/Boston", None])
def test_blocked_navigation_may_end_on_error_page_or_allowed_host(final_url):
    # Chrome shows its own error page after a blocked navigation; that is not a web host.
    evidence = good_evidence()
    evidence["redirect"]["final_url"] = final_url
    evidence["meta_refresh"]["final_url"] = final_url
    assert check.judge(evidence)[0]


def test_redirect_reaching_another_host_fails():
    evidence = good_evidence()
    evidence["redirect"] = {"blocked_hosts": [], "final_url": "https://en.wiktionary.org/wiki/Boston", "status": 200}
    assert not check.judge(evidence)[0]


def test_no_redirect_is_a_note_not_a_pass_claim():
    evidence = good_evidence()
    evidence["redirect"] = {"blocked_hosts": [], "final_url": "https://en.wikipedia.org/wiki/Special:GoToInterwiki/wikt:Boston", "status": 200}
    passed, lines = check.judge(evidence)
    assert passed and any(line.startswith("NOTE: the server did not redirect") for line in lines)


class FakeRequest:
    def __init__(self, url):
        self.url, self.failure = url, "net::ERR_FAILED"


class FakePage:
    """Plays the browser: each set_content 'requests' a fixed set of URLs."""

    def __init__(self, desktop):
        self.desktop, self.handlers, self.url = desktop, {}, "about:blank"

    def on(self, event, handler):
        self.handlers[event] = handler

    def set_content(self, html, **kwargs):
        if "blocked.css" in html:
            self.handlers["requestfinished"](FakeRequest(check.ALLOWED_CSS))
            for url, layer in check.MUST_NOT_LOAD.items():
                if layer == "filter":
                    self.desktop.blocked_requests.append(url)
                else:
                    self.handlers["requestfailed"](FakeRequest(url))
        else:
            self.desktop.blocked_requests.append(check.REFRESH_TARGET)

    def wait_for_timeout(self, ms):
        pass


class FakeDesktop:
    def __init__(self):
        self.blocked_requests, self.last_navigation_status = [], None
        self.page = FakePage(self)

    def navigate(self, url):
        assert url == check.REDIRECT_SOURCE
        self.blocked_requests.append("https://en.wiktionary.org/wiki/Boston")


def test_collect_records_layers_and_hops_from_browser_events():
    evidence = check.collect(FakeDesktop())
    assert evidence["subresources"][check.ALLOWED_CSS] == "loaded"
    assert evidence["subresources"]["https://example.com/blocked.png"] == "blocked_by_filter"
    assert evidence["subresources"]["https://10.0.0.1/private.png"] == "failed_elsewhere"
    assert evidence["meta_refresh"] == {"blocked": True, "final_url": "about:blank"}
    assert evidence["redirect"]["blocked_hosts"] == ["en.wiktionary.org"]
    assert check.judge(evidence)[0]


def test_main_requires_key_before_any_cloud_call(monkeypatch):
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    monkeypatch.setattr("crescendo_agent.local_env.load_local_env", lambda: None)
    with pytest.raises(SystemExit, match="E2B_API_KEY"):
        check.main()


# Public-web mode ---------------------------------------------------------------

def public_evidence():
    states = {url: "loaded" for url in check.PUBLIC_MUST_LOAD}
    states.update({url: ("blocked_by_filter" if layer == "filter" else "failed_elsewhere")
                   for url, layer in check.PUBLIC_MUST_NOT_LOAD.items()})
    return {"subresources": states, "network_errors": {}}


def test_public_boundary_passes():
    assert check.judge_public(public_evidence())[0]


@pytest.mark.parametrize("url", list(check.PUBLIC_MUST_NOT_LOAD))
def test_public_any_private_or_rebinding_load_fails(url):
    evidence = public_evidence()
    evidence["subresources"][url] = "loaded"
    assert not check.judge_public(evidence)[0]


def test_public_rebinding_name_is_not_expected_from_the_filter():
    # The filter sees only a public-looking name, so the firewall's failure counts.
    assert check.PUBLIC_MUST_NOT_LOAD["https://10.0.0.1.sslip.io/rebind.css"] == "any"


@pytest.mark.parametrize("url", list(check.PUBLIC_MUST_LOAD))
def test_public_sites_must_actually_load(url):
    evidence = public_evidence()
    evidence["subresources"][url] = "failed_elsewhere"
    assert not check.judge_public(evidence)[0]
