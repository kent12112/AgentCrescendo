"""Shared, side-effect-free Writer settings, network probes, and output checks."""
import difflib

NO_INTERNET = {"deny_out": ["0.0.0.0/0"], "allow_public_traffic": False}
# Only for --install: Ubuntu's package servers, allowed by name. This is a probe
# convenience; the real feature should use a custom template with Writer preinstalled
# so the writer desktop never needs any network access.
UBUNTU_PACKAGE_HOSTS = ("archive.ubuntu.com", "security.ubuntu.com")

DOC_PATH = "/home/user/letter.odt"
PDF_PATH = "/home/user/letter.pdf"

# Pin the screen size: the visible PDF export clicks a toolbar button by position.
SCREEN = (1024, 768)
# Writer's "Export Directly as PDF" toolbar button (red PDF icon left of Print) at
# 1024x768 with the default toolbar, measured from run 3's 2-typed.png.
EXPORT_PDF_BUTTON = (160, 96)
EXPORT_WAIT_SECONDS = 20

# Writer runs with its own fresh settings folder, so a stored setting from the image
# can't interfere, and the settings below are applied before the first start.
WRITER_PROFILE = "/home/user/writer-profile"
# Every setting here is set to false. Names follow LibreOffice's settings schema
# (from memory, so the probe checks each one exists in the guest's main.xcd).
WRITER_SETTINGS_OFF = {
    # AutoCorrect "while typing" options shared by all LibreOffice apps.
    "/org.openoffice.Office.Common/AutoCorrect": (
        "UseReplacementTable", "TwoCapitalsAtStart", "CapitalAtStartSentence",
        "ChangeUnderlineWeight", "SetInetAttribute", "ChangeOrdinalNumber",
        "AddNonBreakingSpace", "ChangeDash", "RemoveDoubleSpaces",
        "ReplaceSingleQuote", "ReplaceDoubleQuote", "CorrectAccidentalCapsLock"),
    # Word completion: a suggestion accepted by Enter would change the text.
    "/org.openoffice.Office.Writer/AutoFunction/Completion": ("Enable",),
    # The first-start "Tip of the Day" dialog, which could take keyboard focus.
    "/org.openoffice.Office.Common/Misc": ("ShowTipOfTheDay",),
}


def settings_xcu(settings: dict) -> str:
    """LibreOffice's user settings file (registrymodifications.xcu), all values false."""
    items = "".join(
        f'<item oor:path="{path}"><prop oor:name="{name}" oor:op="fuse">'
        f"<value>false</value></prop></item>\n"
        for path, names in settings.items() for name in names)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
            'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            f"{items}</oor:items>\n")
MAX_PDF_BYTES = 5 * 1024 * 1024
WINDOW_WAIT_SECONDS = 60
SAVE_WAIT_SECONDS = 20

# Typographic characters AutoCorrect substitutes by default, mapped back to what was
# typed. Its "Replace dashes" option turns " -- " into an en dash, so the dashes map
# back to two hyphens, not one.
AUTOCORRECT_UNDO = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                                  "–": "--", "—": "--"})


def network_config(install: bool) -> dict:
    """E2B network settings: nothing reachable, or (with --install) only Ubuntu mirrors.

    E2B opens its DNS servers (default 8.8.8.8, on all ports) only when allow_out
    names a domain (SDK docstring, e2b 2.63.0; measured open in docs/e2b-preflight.md).
    So --install also passes dns_servers=[]: the mirrors are then reached through
    /etc/hosts entries, which works because E2B routes allowed names by name.
    """
    # Build fresh lists so a caller can never edit the NO_INTERNET constant through them.
    config = {**NO_INTERNET, "deny_out": list(NO_INTERNET["deny_out"])}
    if install:
        config["allow_out"] = list(UBUNTU_PACKAGE_HOSTS)
        config["dns_servers"] = []
    return config


# Any public address will do: E2B ignores the guest's chosen IP for allowed names.
# 192.0.2.1 is reserved for documentation, so it can never be a real destination.
HOSTS_LINES = "".join(f"192.0.2.1 {host}\n" for host in UBUNTU_PACKAGE_HOSTS)

# Runs inside the guest. Every check runs at the same time in its own thread, with
# one shared deadline, because a blocked DNS lookup ignores socket timeouts and keeps
# retrying (live run 1, November 17, 2026: a single urlopen check hung > 20 s).
#
# Only a server-proven answer counts as reachable, as in the preflight: a TLS
# handshake whose certificate verifies for the server's real name, or a DNS reply
# carrying our random query ID. A plain TCP connect proves nothing here: E2B's proxy
# accepts every TCP connection itself and judges afterwards (live run 2: 8.8.8.8 and
# 1.1.1.1 "connected"; the preflight hit the same trap on November 16). TCP connect is
# still recorded under "info" so that behavior stays visible.
#
# Prints one JSON line: {"checks": {name: outcome}, "info": {...}}. Outcomes:
#   answered     the real server replied: the desktop is NOT offline
#   other_answer a TLS server answered with a certificate not valid for that name
#   blocked      connection cut or refused, or no reply
#   timeout      still waiting at the deadline (no answer)
GUEST_NETWORK_CHECK = r"""
import json, os, socket, ssl, threading, time
LIMIT = 5

def lookup():
    socket.getaddrinfo("example.com", 443)
    return "answered"

def dns_udp(server):
    def check():
        query_id = os.urandom(2)
        question = b"\x07example\x03com\x00"
        packet = query_id + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + question + b"\x00\x01\x00\x01"
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(LIMIT)
            sock.sendto(packet, (server, 53))
            reply, _ = sock.recvfrom(512)
        return "answered" if reply[:2] == query_id else "blocked"
    return check

def tls(ip, name):
    def check():
        with socket.create_connection((ip, 443), timeout=LIMIT) as raw:
            try:
                with ssl.create_default_context().wrap_socket(raw, server_hostname=name):
                    return "answered"
            except ssl.SSLCertVerificationError:
                return "other_answer"
    return check

def tcp_connect(ip, port):
    def check():
        socket.create_connection((ip, port), timeout=LIMIT).close()
        return "connected"
    return check

checks = {"dns lookup example.com": lookup,
          "udp dns 8.8.8.8": dns_udp("8.8.8.8"), "tls 8.8.8.8 dns.google": tls("8.8.8.8", "dns.google"),
          "udp dns 1.1.1.1": dns_udp("1.1.1.1"), "tls 1.1.1.1 one.one.one.one": tls("1.1.1.1", "one.one.one.one")}
info = {"tcp connect 8.8.8.8:443": tcp_connect("8.8.8.8", 443),
        "tcp connect 1.1.1.1:443": tcp_connect("1.1.1.1", 443)}
results = {}

def run(name, fn):
    try:
        results[name] = fn()
    except Exception as exc:
        results[name] = "blocked"
        results[name + " error"] = type(exc).__name__

everything = {**checks, **info}
threads = [threading.Thread(target=run, args=item, daemon=True) for item in everything.items()]
for thread in threads:
    thread.start()
deadline = time.monotonic() + 2 * LIMIT + 1  # Connect + handshake; one shared deadline.
for thread in threads:
    thread.join(max(0, deadline - time.monotonic()))

def outcome(name):
    value = results.get(name, "timeout")
    error = results.get(name + " error")
    return value + (" (" + error + ")" if error else "")

print(json.dumps({"checks": {name: outcome(name) for name in checks},
                  "info": {name: outcome(name) for name in info}}))
"""
NETWORK_CHECKS = ("dns lookup example.com", "udp dns 8.8.8.8", "tls 8.8.8.8 dns.google",
                  "udp dns 1.1.1.1", "tls 1.1.1.1 one.one.one.one")


def judge_network(checks: dict) -> str | None:
    """Return a problem, or None if no server answered any check.

    Outcomes may carry the error name, e.g. "blocked (SSLEOFError)". "timeout" means
    no answer came back, so it counts as blocked. "other_answer" fails: something
    answered, even if not the real server. A missing or unknown result fails as
    "not measured".
    """
    for name in NETWORK_CHECKS:
        outcome = str(checks.get(name, "missing")).split(" (")[0]
        if outcome in {"answered", "other_answer"}:
            return f"{name}: a server answered ({outcome}); the desktop is not offline."
        if outcome not in {"blocked", "timeout"}:
            return f"{name} was not measured ({checks.get(name)!r})."
    return None


def text_differences(expected: str, actual: str, limit: int = 10) -> list[tuple[str, str]]:
    """Word-level differences as (expected, actual) pairs; [] means the same words.

    Whitespace is ignored because a PDF's line breaks follow the page width, not the
    typed text.
    """
    a, b = expected.split(), actual.split()
    found = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            found.append((" ".join(a[i1:i2]), " ".join(b[j1:j2])))
            if len(found) >= limit:
                break
    return found


def compare_text(expected: str, actual: str) -> dict:
    """Did the PDF keep the typed words? Separates AutoCorrect edits from lost keys."""
    raw = text_differences(expected, actual)
    undone = text_differences(expected, actual.translate(AUTOCORRECT_UNDO))
    return {"exact": not raw, "same_after_autocorrect_undo": not undone,
            "differences": raw, "differences_after_undo": undone}


def pdf_words_match(expected: str, actual: str) -> bool:
    """Match words, ignoring PDF line wrapping and a hyphen's no-break property.

    LibreOffice exports U+2011 NON-BREAKING HYPHEN as U+002D in the PDF text
    layer. This is a layout distinction, like the line breaks already ignored by
    compare_text. Do not normalize quotes, other dashes, accents, letters or digits.
    The original Unicode remains the keyboard input and approved snapshot.
    """
    return compare_text(expected.replace("\u2011", "-"), actual.replace("\u2011", "-"))["exact"]


def typing_plan(text: str) -> list[str | None]:
    """Split text into lines to type, with None meaning "press the Enter key".

    The SDK's write() passes "\\n" to `xdotool type`, and Writer ignored every one
    (live run 3, November 17, 2026: the whole letter became one paragraph). Pressing
    the real Return key between lines works the way a person types. Empty lines
    produce no text, only the Enter press, so blank lines between paragraphs survive.
    """
    plan = []
    for index, line in enumerate(text.split("\n")):
        if index:
            plan.append(None)
        if line:
            plan.append(line)
    return plan


def looks_like_pdf(data: bytes) -> str | None:
    """Return a problem with the downloaded bytes, or None if they look like a PDF."""
    if len(data) > MAX_PDF_BYTES:
        return f"PDF is {len(data)} bytes, over the {MAX_PDF_BYTES}-byte limit."
    if not data.startswith(b"%PDF-"):
        return "Downloaded file does not start with %PDF-."
    return None


