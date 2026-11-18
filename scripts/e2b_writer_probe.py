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
from crescendo_agent.writer_support import (
    NO_INTERNET,
    UBUNTU_PACKAGE_HOSTS,
    DOC_PATH,
    PDF_PATH,
    SCREEN,
    EXPORT_PDF_BUTTON,
    EXPORT_WAIT_SECONDS,
    WRITER_PROFILE,
    WRITER_SETTINGS_OFF,
    settings_xcu,
    MAX_PDF_BYTES,
    WINDOW_WAIT_SECONDS,
    SAVE_WAIT_SECONDS,
    AUTOCORRECT_UNDO,
    network_config,
    HOSTS_LINES,
    GUEST_NETWORK_CHECK,
    NETWORK_CHECKS,
    judge_network,
    text_differences,
    compare_text,
    typing_plan,
    looks_like_pdf,
)

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
