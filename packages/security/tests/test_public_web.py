"""Public-web mode (W1X-F02, F03): any public site, never an internal host."""
import pytest

from crescendo_security.policy import (
    PRIVATE_NETWORKS, TaskGrant, ToolCall, authorize, authorize_destination,
)

PUBLIC = TaskGrant("public", frozenset({"navigate", "click", "finish"}), frozenset(), public_web=True)
ALLOWLIST = TaskGrant("list", frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))


def test_existing_grants_default_to_allowlist_mode():
    assert ALLOWLIST.public_web is False


@pytest.mark.parametrize("url", ["https://www.boston.gov/", "https://example.com/a?b=c",
                                 "https://en.wikipedia.org/wiki/Boston", "https://sub.Example.CO.uk/"])
def test_public_sites_are_permitted_destinations(url):
    assert authorize_destination(PUBLIC, url).allowed


@pytest.mark.parametrize("url", [
    "https://10.0.0.1/", "https://169.254.169.254/latest/", "https://[::1]/", "https://[fd00::1]/",
    "https://8.8.8.8/",                       # even public addresses: names only
    "https://2130706433/", "https://0x7f.1/", "https://127.1/", "https://foo.0x7f/",  # browser IPv4 forms
    "https://localhost/", "https://app.localhost/", "https://printer.local/", "https://db.internal/",
    "https://router.home.arpa/", "https://intranet/",                                  # internal names
    "http://example.com/", "https://example.com:8443/", "https://user:pw@example.com/",
    "ftp://example.com/", "https:///nohost",
])
def test_internal_or_unsafe_destinations_are_refused(url):
    assert not authorize_destination(PUBLIC, url).allowed


def test_model_navigate_reaches_any_public_site_but_not_internal_ones():
    # Open browsing (decision 0005): the model may name a public site itself.
    assert authorize(PUBLIC, ToolCall("navigate", {"url": "https://example.com/a?q=b"})).allowed
    for url in ("https://10.0.0.1/", "https://localhost/", "http://example.com/"):
        assert not authorize(PUBLIC, ToolCall("navigate", {"url": url})).allowed, url
    no_tool = TaskGrant("n", frozenset({"click"}), frozenset(), public_web=True)
    assert not authorize(no_tool, ToolCall("navigate", {"url": "https://example.com/"})).allowed


def test_allowlist_mode_still_uses_exact_hosts():
    assert authorize(ALLOWLIST, ToolCall("navigate", {"url": "https://en.wikipedia.org/wiki/X"})).allowed
    assert not authorize_destination(ALLOWLIST, "https://example.com/").allowed
    assert not authorize_destination(ALLOWLIST, "https://user@en.wikipedia.org/").allowed


def test_destination_check_does_not_depend_on_tools():
    # The browser filter checks every page request; that must not need a model tool.
    no_tools = TaskGrant("t", frozenset(), frozenset({"en.wikipedia.org"}))
    assert authorize_destination(no_tools, "https://en.wikipedia.org/w/load.php").allowed


def test_private_networks_cover_metadata_and_rfc1918():
    import ipaddress
    nets = [ipaddress.ip_network(n) for n in PRIVATE_NETWORKS]
    for ip in ("10.9.8.7", "172.20.0.1", "192.168.50.1", "169.254.169.254", "100.100.100.100", "127.0.0.2"):
        assert any(ipaddress.ip_address(ip) in n for n in nets), ip
    for ip in ("8.8.8.8", "1.0.0.1", "93.184.215.14"):
        assert not any(ipaddress.ip_address(ip) in n for n in nets), ip
