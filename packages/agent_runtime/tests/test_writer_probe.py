"""Offline tests for scripts/e2b_writer_probe.py's pure checks (JOB-P01)."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "e2b_writer_probe.py"
spec = importlib.util.spec_from_file_location("e2b_writer_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_default_network_denies_everything_and_allows_nothing():
    config = probe.network_config(install=False)
    assert config == {"deny_out": ["0.0.0.0/0"], "allow_public_traffic": False}
    assert "allow_out" not in config


def test_install_network_allows_only_ubuntu_package_servers_and_no_dns():
    config = probe.network_config(install=True)
    assert config["deny_out"] == ["0.0.0.0/0"]
    assert config["allow_out"] == ["archive.ubuntu.com", "security.ubuntu.com"]
    # Without this, naming a domain opens E2B's default DNS server 8.8.8.8 on all ports.
    assert config["dns_servers"] == []
    assert config["allow_public_traffic"] is False


def test_hosts_lines_name_each_mirror_with_a_documentation_address():
    assert probe.HOSTS_LINES == ("192.0.2.1 archive.ubuntu.com\n"
                                 "192.0.2.1 security.ubuntu.com\n")


def test_guest_network_check_is_valid_python_covering_every_check():
    compile(probe.GUEST_NETWORK_CHECK, "guest", "exec")
    for name in probe.NETWORK_CHECKS:
        assert f'"{name}"' in probe.GUEST_NETWORK_CHECK


def test_tcp_connect_is_information_not_a_judged_check():
    # E2B's proxy accepts every TCP connection before judging it (live run 2), so a
    # TCP connect must never decide reachability.
    assert not any(name.startswith("tcp") for name in probe.NETWORK_CHECKS)
    assert '"tcp connect 8.8.8.8:443"' in probe.GUEST_NETWORK_CHECK


ALL_BLOCKED = {name: "blocked (SSLEOFError)" for name in probe.NETWORK_CHECKS}


def test_live_run_2_shape_passes_when_only_tcp_connected():
    # Run 2's TCP "connections" now sit in info; with no server answer, it passes.
    checks = {**ALL_BLOCKED, "dns lookup example.com": "timeout", "udp dns 8.8.8.8": "blocked (timeout)"}
    assert probe.judge_network(checks) is None


@pytest.mark.parametrize("change, phrase", [
    ({"tls 8.8.8.8 dns.google": "answered"}, "a server answered"),
    ({"udp dns 1.1.1.1": "answered"}, "a server answered"),
    ({"dns lookup example.com": "answered"}, "a server answered"),
    ({"tls 1.1.1.1 one.one.one.one": "other_answer"}, "a server answered"),
    ({"udp dns 8.8.8.8": "connected"}, "not measured"),
])
def test_network_fails_when_a_server_answers_or_result_is_unknown(change, phrase):
    assert phrase in probe.judge_network({**ALL_BLOCKED, **change})


def test_network_fails_when_a_check_is_missing():
    checks = dict(ALL_BLOCKED)
    del checks["udp dns 8.8.8.8"]
    assert "not measured" in probe.judge_network(checks)


def test_network_config_returns_a_copy():
    probe.network_config(install=False)["deny_out"].append("x")
    assert probe.NO_INTERNET["deny_out"] == ["0.0.0.0/0"]


def test_typing_plan_presses_enter_for_every_line_break():
    assert probe.typing_plan("Alex\nalex@example.com\n\nDear team,\n") == [
        "Alex", None, "alex@example.com", None, None, "Dear team,", None]


def test_typing_plan_never_sends_a_newline_as_text():
    plan = probe.typing_plan(probe.SAMPLE_LETTER)
    assert all("\n" not in part for part in plan if part is not None)
    assert plan.count(None) == probe.SAMPLE_LETTER.count("\n")
    assert "".join("\n" if part is None else part for part in plan) == probe.SAMPLE_LETTER


def test_words_glued_at_lost_line_breaks_are_reported():
    # Live run 3's failure shape: Enter presses lost, so lines ran together.
    result = probe.compare_text("Alex Rivera\nalex.rivera@example.com", "Alex Riveraalex.rivera@example.com")
    assert not result["same_after_autocorrect_undo"]


def test_pdf_line_breaks_do_not_count_as_differences():
    typed = "Dear Hiring Team,\n\nI am applying for the role."
    from_pdf = "Dear Hiring\nTeam, I am applying for\nthe role."
    assert probe.compare_text(typed, from_pdf)["exact"]


def test_autocorrect_typography_is_separated_from_lost_words():
    typed = "I'm applying -- \"quoted\" text."
    from_pdf = "I’m applying – “quoted” text."
    result = probe.compare_text(typed, from_pdf)
    assert not result["exact"]
    assert result["same_after_autocorrect_undo"]


def test_dropped_characters_are_reported():
    result = probe.compare_text("cut latency to 0.6 seconds", "cut latncy to 0.6 seconds")
    assert not result["same_after_autocorrect_undo"]
    assert result["differences_after_undo"] == [("latency", "latncy")]


def test_differences_are_limited():
    typed = " ".join(f"w{i}" for i in range(50))
    garbled = " ".join(f"x{i}" if i % 2 else f"w{i}" for i in range(50))
    assert len(probe.text_differences(typed, garbled, limit=3)) == 3


@pytest.mark.parametrize("data, ok", [
    (b"%PDF-1.7\n...", True),
    (b"<html>not a pdf</html>", False),
    (b"%PDF-" + b"0" * probe.MAX_PDF_BYTES, False),
])
def test_downloaded_bytes_must_look_like_a_small_pdf(data, ok):
    assert (probe.looks_like_pdf(data) is None) is ok


def test_settings_file_is_valid_xml_with_every_setting_false():
    from xml.etree import ElementTree

    root = ElementTree.fromstring(probe.settings_xcu(probe.WRITER_SETTINGS_OFF))
    oor = "{http://openoffice.org/2001/registry}"
    found = {(item.get(oor + "path"), prop.get(oor + "name")): prop.findtext("value")
             for item in root for prop in item}
    expected = {(path, name) for path, names in probe.WRITER_SETTINGS_OFF.items() for name in names}
    assert set(found) == expected
    assert set(found.values()) == {"false"}


def test_settings_cover_the_changes_seen_in_run_4():
    # Run 4: curly quotes, en dash, and the email turned into a link.
    common = probe.WRITER_SETTINGS_OFF["/org.openoffice.Office.Common/AutoCorrect"]
    assert {"ReplaceSingleQuote", "ReplaceDoubleQuote", "ChangeDash", "SetInetAttribute"} <= set(common)


def test_default_typing_is_slow_enough_to_watch(monkeypatch):
    monkeypatch.setattr("sys.argv", ["probe"])
    import argparse
    captured = {}
    real_parse = argparse.ArgumentParser.parse_args

    def stop_after_parse(self, *args, **kwargs):
        captured["args"] = real_parse(self, *args, **kwargs)
        raise SystemExit(0)

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", stop_after_parse)
    with pytest.raises(SystemExit):
        probe.main()
    assert captured["args"].delay_ms == 50
    assert captured["args"].autocorrect is False


def test_sample_letter_is_fictional():
    assert "example.com" in probe.SAMPLE_LETTER
    assert "Example Robotics" in probe.SAMPLE_LETTER
