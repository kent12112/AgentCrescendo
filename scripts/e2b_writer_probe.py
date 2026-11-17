"""Live probe (JOB-P01): can an E2B desktop with no internet type a letter into
LibreOffice Writer and hand the host a PDF?

Why: the planned cover-letter writer drafts and checks the letter on the host, then
types it visibly on a separate desktop that cannot reach the internet. Resume-derived
text then has nowhere to go except the PDF the host downloads (decision 0007 keeps
resume data off browsing desktops).

No model calls. The letter is a fixed, fictional sample: no real resume data.

Steps, each timed and recorded in result.json under .demo-artifacts/writer-probe-<id>/:
  network   no server answers from the guest (DNS reply or verified TLS)
  office    is LibreOffice present? (installed only with --install); our settings
            names checked against its schema
  launch    open Writer with a fresh settings folder (AutoCorrect, word completion and
            the tip dialog off) and wait for its window
  type      real keystrokes, Return between lines; characters per second
  save      Ctrl+S, type a path into the save dialog, Enter; wait for the file
  pdf       visible: click "Export Directly as PDF", type the path, Enter. If no PDF
            appears, the hidden converter is used and the run is NOT a pass
  download  read the PDF through E2B's file API; check it is a PDF; extract its text
  compare   extracted text vs. what was typed: must match word for word
            (with --autocorrect, typography changes are allowed and reported)

The desktop is killed in a finally block; E2B's lifetime timer is the backstop.

    python scripts/e2b_writer_probe.py [--watch] [--install] [--autocorrect] [--delay-ms 50]
"""
import argparse
from contextlib import nullcontext
import difflib
import json
from pathlib import Path
import shlex
import time
from uuid import uuid4
import webbrowser

from crescendo_agent.local_env import load_local_env

# Deny every outbound IPv4 address. Same shape as the allowlist mode in e2b_desktop.py,
# with an empty allowlist. allow_public_traffic=False keeps the desktop's own URLs
# (the viewer stream) behind E2B's access token.
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

# Fictional applicant and company. It includes an apostrophe, quotes, and a double
# hyphen on purpose: LibreOffice's default AutoCorrect rewrites those, and the
# probe should show whether it does.
SAMPLE_LETTER = """Alex Rivera
alex.rivera@example.com

November 17, 2026

Hiring Team
Example Robotics

Dear Hiring Team,

I'm applying for the Applied AI Engineer role at Example Robotics. Your posting asks for "production experience with Python and LLM tooling" -- that is the work I have done for the past four years.

At my last company I built a retrieval service in Python and FastAPI that answered support questions with cited sources, and I cut its median latency from 2.1 seconds to 0.6 seconds. I also wrote the evaluation suite that caught regressions before each release.

I would welcome the chance to bring that experience to your team.

Sincerely,
Alex Rivera
"""

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


class StepLog:
    """Run named steps in order, timing each and stopping at the first failure."""

    def __init__(self):
        self.steps = []

    def run(self, name, fn):
        start = time.monotonic()
        try:
            detail, ok = fn(), True
        except Exception as error:  # A probe reports every failure instead of crashing.
            detail, ok = f"{type(error).__name__}: {error}"[:800], False
        record = {"step": name, "ok": ok, "seconds": round(time.monotonic() - start, 1),
                  "detail": detail}
        self.steps.append(record)
        print(f"[{'ok' if ok else 'FAIL'}] {name} ({record['seconds']} s): {detail}", flush=True)
        if not ok:
            raise StopProbe(name)
        return detail


class StopProbe(Exception):
    """A step failed; the remaining steps depend on it."""


def run_probe(sandbox, args, directory: Path, log: StepLog, facts: dict) -> None:
    """Run every step in order; `facts` keeps what was learned even if a step fails."""
    from e2b import CommandExitException

    def shot(name):
        (directory / name).write_bytes(sandbox.screenshot(format="bytes"))

    def succeeds(command, **kwargs) -> bool:
        try:
            sandbox.commands.run(command, **kwargs)
            return True
        except CommandExitException:
            return False

    def network():
        # `timeout 20` ends the guest program itself, so the host call (35 s) can't hang.
        output = sandbox.commands.run(
            "timeout 20 python3 -c " + shlex.quote(GUEST_NETWORK_CHECK), timeout=35).stdout
        report = json.loads(output.strip().splitlines()[-1])
        facts["network"] = report
        problem = judge_network(report["checks"])
        if problem:
            raise RuntimeError(f"{problem} Report: {report}")
        return f"no server answered: {report['checks']} (info: {report['info']})"

    def office():
        present = succeeds("command -v soffice", timeout=10)
        facts["preinstalled"] = present
        if not present:
            if not args.install:
                raise RuntimeError("LibreOffice is not installed. Rerun with --install to try "
                                   "installing it through Ubuntu's package servers.")
            # No DNS server is reachable (dns_servers=[]), so name the mirrors locally.
            sandbox.commands.run("printf %s " + shlex.quote(HOSTS_LINES) + " >> /etc/hosts",
                                 user="root", timeout=10)
            sandbox.commands.run(
                "apt-get update -q && DEBIAN_FRONTEND=noninteractive apt-get install -y -q "
                "--no-install-recommends libreoffice-writer",
                user="root", timeout=args.install_timeout)
        version = sandbox.commands.run("soffice --version", timeout=60).stdout.strip()
        facts["version"] = version
        detail = ("preinstalled: " if present else "installed: ") + version
        if not args.autocorrect:
            # Check our setting names against the guest's own settings schema. Only
            # a sanity check: the exact text comparison is the real proof.
            names = sorted({name for names in WRITER_SETTINGS_OFF.values() for name in names})
            schema = sandbox.commands.run(
                "cat $(find /usr/lib/libreoffice /opt -name main.xcd 2>/dev/null | head -1)",
                timeout=20).stdout
            missing = [name for name in names if f'oor:name="{name}"' not in schema]
            facts["settings_missing_from_schema"] = missing
            detail += f"; settings names missing from schema: {missing or 'none'}"
        return detail

    def launch():
        profile = ""
        if not args.autocorrect:
            sandbox.files.write(f"{WRITER_PROFILE}/user/registrymodifications.xcu",
                                settings_xcu(WRITER_SETTINGS_OFF))
            profile = f"-env:UserInstallation=file://{WRITER_PROFILE} "
        handle = sandbox.commands.run(f"soffice {profile}--writer --norestore --nologo "
                                      "> /tmp/writer.log 2>&1",
                                      background=True, timeout=0)
        handle.disconnect()
        deadline = time.monotonic() + WINDOW_WAIT_SECONDS
        window = ""
        while time.monotonic() < deadline and not window:
            try:
                found = sandbox.commands.run(
                    "xdotool search --onlyvisible --name 'LibreOffice Writer'", timeout=10)
                window = found.stdout.split()[-1] if found.stdout.split() else ""
            except CommandExitException:  # No matching window yet.
                time.sleep(1)
        if not window:
            shot("1-launch-failed.png")
            raise RuntimeError(f"No Writer window within {WINDOW_WAIT_SECONDS} s.")
        time.sleep(3)  # Let a first-run "Tip of the Day" dialog appear, if any...
        sandbox.press("escape")  # ...and close it. Escape is harmless in an empty document.
        sandbox.commands.run(f"xdotool windowactivate --sync {window}", timeout=10)
        width, height = sandbox.get_screen_size()
        sandbox.left_click(width // 2, height // 2)  # Put the cursor on the page.
        shot("1-writer-open.png")
        return f"window {window}; screen {width}x{height}"

    def type_letter():
        start = time.monotonic()
        for part in typing_plan(SAMPLE_LETTER):
            if part is None:
                sandbox.press("enter")
            else:
                sandbox.write(part, chunk_size=args.chunk_size, delay_in_ms=args.delay_ms)
        seconds = time.monotonic() - start
        facts["chars"] = len(SAMPLE_LETTER)
        facts["chars_per_second"] = round(len(SAMPLE_LETTER) / seconds, 1)
        shot("2-typed.png")
        return f"{len(SAMPLE_LETTER)} characters in {seconds:.1f} s ({facts['chars_per_second']}/s)"

    def save():
        sandbox.press(["ctrl", "s"])
        time.sleep(2)  # Wait for the save dialog; its file-name field starts selected.
        shot("3-save-dialog.png")
        sandbox.write(DOC_PATH, chunk_size=50, delay_in_ms=10)  # Replaces the suggested name.
        sandbox.press("enter")
        deadline = time.monotonic() + SAVE_WAIT_SECONDS
        while time.monotonic() < deadline:
            if succeeds(f"test -s {DOC_PATH}", timeout=10):
                shot("4-saved.png")
                return f"saved {DOC_PATH}"
            time.sleep(1)
        shot("4-save-failed.png")
        raise RuntimeError(f"{DOC_PATH} did not appear within {SAVE_WAIT_SECONDS} s.")

    def pdf():
        # Visible first: click "Export Directly as PDF", type the path into its dialog.
        sandbox.left_click(*EXPORT_PDF_BUTTON)
        time.sleep(2)
        shot("5-export-dialog.png")
        sandbox.write(PDF_PATH, chunk_size=50, delay_in_ms=10)  # Replaces the suggested name.
        sandbox.press("enter")
        deadline = time.monotonic() + EXPORT_WAIT_SECONDS
        while time.monotonic() < deadline:
            if succeeds(f"test -s {PDF_PATH}", timeout=10):
                time.sleep(1)  # Let Writer finish writing before the host reads the file.
                facts["pdf_export"] = "visible"
                shot("6-exported.png")
                return f"visible export wrote {PDF_PATH}"
            time.sleep(1)
        # Fallback, recorded as such: the run then cannot count as a full pass.
        shot("6-export-failed.png")
        sandbox.press("escape")
        # A separate profile: the open Writer window holds a lock on its own one.
        sandbox.commands.run(
            "soffice -env:UserInstallation=file:///tmp/lo-convert --headless "
            f"--convert-to pdf --outdir /home/user {DOC_PATH}", timeout=120)
        if not succeeds(f"test -s {PDF_PATH}", timeout=10):
            raise RuntimeError("Visible export and the fallback converter both wrote no PDF.")
        facts["pdf_export"] = "fallback"
        return f"VISIBLE EXPORT FAILED; fallback converter wrote {PDF_PATH}"

    def download():
        data = bytes(sandbox.files.read(PDF_PATH, format="bytes"))
        problem = looks_like_pdf(data)
        if problem:
            raise RuntimeError(problem)
        (directory / "letter.pdf").write_bytes(data)
        facts["pdf_bytes"] = len(data)
        return f"{len(data)} bytes saved to {directory / 'letter.pdf'}"

    def compare():
        from io import BytesIO
        from pypdf import PdfReader

        reader = PdfReader(BytesIO((directory / "letter.pdf").read_bytes()))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        (directory / "pdf-text.txt").write_text(text)
        result = compare_text(SAMPLE_LETTER, text)
        facts["comparison"] = result
        if result["exact"]:
            return "PDF text matches the typed letter word for word."
        if not args.autocorrect:
            raise RuntimeError("AutoCorrect was meant to be off, but the text changed: "
                               f"{result['differences']}")
        if result["same_after_autocorrect_undo"]:
            return f"Only AutoCorrect typography differs: {result['differences']}"
        raise RuntimeError(f"Words lost or changed: {result['differences_after_undo']}")

    for name, fn in [("network", network), ("office", office), ("launch", launch),
                     ("type", type_letter), ("save", save), ("pdf", pdf),
                     ("download", download), ("compare", compare)]:
        log.run(name, fn)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--watch", action="store_true",
                        help="Open the desktop in the local live viewer before typing.")
    parser.add_argument("--install", action="store_true",
                        help="If LibreOffice is missing, install it (allows Ubuntu package servers only).")
    parser.add_argument("--delay-ms", type=int, default=50,
                        help="xdotool delay between typed characters; 50 is easy to watch "
                             "(run 4: 20 ms gave 54 characters/s).")
    parser.add_argument("--autocorrect", action="store_true",
                        help="Keep LibreOffice's default AutoCorrect (typography changes allowed).")
    parser.add_argument("--chunk-size", type=int, default=25,
                        help="Characters per xdotool call (SDK default 25).")
    parser.add_argument("--install-timeout", type=int, default=600)
    parser.add_argument("--lifetime", type=int, default=None,
                        help="E2B kill timer in seconds (default 300, or 900 with --install).")
    args = parser.parse_args()
    if not 0 <= args.delay_ms <= 200 or not 1 <= args.chunk_size <= 200:
        parser.error("--delay-ms must be 0-200 and --chunk-size 1-200.")
    lifetime = args.lifetime or (900 if args.install else 300)
    if not 120 <= lifetime <= 1200:
        parser.error("--lifetime must be 120-1200 seconds.")

    load_local_env()
    from e2b_desktop import Sandbox
    if args.watch:
        from crescendo_agent.live_view import open_live_view, wait_for_viewer

    directory = Path(".demo-artifacts") / ("writer-probe-" + uuid4().hex[:12])
    directory.mkdir(parents=True)
    log, facts, stopped_at = StepLog(), {}, None
    started = time.monotonic()
    sandbox = Sandbox.create(resolution=SCREEN, timeout=lifetime, network=network_config(args.install),
                             lifecycle={"on_timeout": "kill"})
    print("Desktop created:", sandbox.sandbox_id, flush=True)
    try:
        with open_live_view(sandbox) if args.watch else nullcontext() as viewer:
            if viewer is not None:
                print("Local live viewer:", viewer.url, flush=True)
                webbrowser.open(viewer.url)
                wait_for_viewer(viewer)
            try:
                run_probe(sandbox, args, directory, log, facts)
            except StopProbe as stop:
                stopped_at = str(stop)
    finally:
        sandbox.kill()
        result = {"sandbox_id": sandbox.sandbox_id, "network": network_config(args.install),
                  "delay_ms": args.delay_ms, "chunk_size": args.chunk_size,
                  "autocorrect": args.autocorrect,
                  # A fallback PDF proves the pipeline but not the visible export.
                  "passed": (stopped_at is None and len(log.steps) == 8
                             and facts.get("pdf_export") == "visible"),
                  "stopped_at": stopped_at,
                  "total_seconds": round(time.monotonic() - started, 1),
                  "steps": log.steps, "facts": facts}
        (directory / "result.json").write_text(json.dumps(result, indent=2))
        print("Desktop killed. Evidence:", directory, flush=True)
    if result["passed"]:
        print("PASSED", flush=True)
    elif stopped_at is None:
        print("NOT PASSED: every step ran, but the PDF came from the fallback converter, "
              "not the visible export. See 5-export-dialog.png and 6-export-failed.png.", flush=True)
    else:
        print(f"STOPPED at {stopped_at}", flush=True)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
