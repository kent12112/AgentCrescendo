"""Isolated browser check: real Next/FastAPI/SQLite, fictional data, fake model only.

Run .venv/bin/python scripts/smoke_job_search.py from the repository root.
Requires installed web dependencies, Playwright, and Microsoft Edge. Starts and
stops its own loopback servers and uses an isolated frontend copy/database.
Default: fake providers only. --live-writer uses E2B for a fictional approved letter;
Groq is still fake and no personal resume or letter is used.
"""
import argparse
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import shutil
import json
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[1]
RESUME = "Alex Example\nalex@example.com\nBuilt Python data pipelines for 3 years. Reduced latency by 25%."
STRESS_PARAGRAPHS = [
    "I’m applying for the frontend engineering internship at Fictional Tools. I build accessible React and TypeScript interfaces, and I care about the details that make software useful. Your team’s focus on collaborative editing matches the work I want to do.",
    "I built a Python service and a React dashboard for a student project. I reduced API latency by 25% and wrote tests for the data-loading states. My work included keyboard navigation, clear validation messages, and documentation that helped teammates ship changes.",
    "I’m interested in your “build together” approach—especially the connection between dependable systems and thoughtful front‑end experiences. My résumé describes hands-on work with PostgreSQL, automated tests, and responsive layouts. I would bring that same care to a team that turns complex problems into clear tools.",
    "Thank you for considering my application. I’d welcome the chance to discuss how my experience can contribute to Fictional Tools and to learn from the engineers building its next chapter.",
]


def serve():
    from datetime import datetime, timedelta, timezone
    import uvicorn
    from sqlalchemy.orm import Session
    from crescendo_api.database import get_engine
    from crescendo_api.letters import Draft, DraftUnavailable, check_draft
    from crescendo_api.main import app
    from crescendo_api.models import Base, JobPosting
    from crescendo_api.routes.letters import draft_generator

    engine = get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for number in range(55):
            session.add(JobPosting(source="ashby", posting_id=f"00000000-0000-4000-8000-{number:012d}",
                company_slug=f"fictional-{number}", company_name=f"Fictional Co {number}",
                title="AI Engineer", url=f"https://jobs.ashbyhq.com/fictional-{number}/00000000-0000-4000-8000-{number:012d}",
                description="We build tools for developers. Python required. Three years of experience.",
                countries=["United States"], locations=["New York"], workplace="hybrid",
                published_at=datetime.now(timezone.utc) - timedelta(days=1),
                first_seen_at=datetime.now(timezone.utc), last_seen_at=datetime.now(timezone.utc)))
        session.commit()
    attempts = {}

    def fake(inputs, posting, _key):
        key = posting["posting_id"]
        attempts[key] = attempts.get(key, 0) + 1
        time.sleep(0.3)
        if posting["company_notes"] == "simulate failure" and attempts[key] == 1:
            raise DraftUnavailable("Controlled provider failure. Retry this letter.")
        if os.environ.get("SMOKE_WRITER_STRESS") == "1":
            draft = Draft.model_validate({"paragraphs": [[{"text": paragraph, "source": "resume", "quote": "Built Python data pipelines for 3 years."}] for paragraph in STRESS_PARAGRAPHS]})
            return check_draft(draft, inputs["resume"], posting)
        draft = Draft.model_validate({"paragraphs": [[{
            "text": "My Python pipeline work is relevant to your tools for developers.", "source": "resume",
            "quote": "Built Python data pipelines for 3 years.", "supporting_quotes": [{
                "source": "posting", "quote": "We build tools for developers."}]}], [{
            "text": "Your team builds tools for developers.", "source": "posting",
            "quote": "We build tools for developers."}]]})
        return check_draft(draft, inputs["resume"], posting)

    app.dependency_overrides[draft_generator] = lambda: fake
    if os.environ.get("SMOKE_REAL_WRITER") == "1" and os.environ.get("SMOKE_WRITER_STRESS") == "1":
        # Fictional-only test evidence. Production never saves unverified PDFs.
        from crescendo_agent import writer as writer_runtime
        original_verify = writer_runtime.verify_pdf
        original_wait = writer_runtime.OfflineWriter._wait_file

        def capture_document(desktop, path, checkpoint):
            original_wait(desktop, path, checkpoint)
            if path == writer_runtime.DOC_PATH:
                folder = Path(os.environ["SMOKE_WRITER_ARTIFACTS"])
                (folder / "writer-raw.odt").write_bytes(bytes(desktop.sandbox.files.read(path, format="bytes")))

        writer_runtime.OfflineWriter._wait_file = capture_document

        def capture_pdf(data, expected):
            folder = Path(os.environ["SMOKE_WRITER_ARTIFACTS"])
            (folder / "writer-raw.pdf").write_bytes(data)
            original_verify(data, expected)

        writer_runtime.verify_pdf = capture_pdf
    if os.environ.get("SMOKE_REAL_WRITER") != "1":
        from io import BytesIO
        import threading
        from types import SimpleNamespace
        from fastapi.responses import HTMLResponse
        from pypdf import PdfWriter
        from crescendo_api.writer_service import WriterManager, get_writer_manager

        desktops = []

        class FakeWriter:
            def __init__(self, key):
                self.viewer = SimpleNamespace(url=f"http://127.0.0.1:{os.environ['SMOKE_API_PORT']}/watch/" + "a" * 40,
                                              connected=threading.Event())
                desktops.append(self)

            def open(self):
                pass

            def prepare(self, checkpoint):
                checkpoint()

            def write_pdf(self, text, progress, checkpoint):
                progress("typing", 0)
                time.sleep(2)
                checkpoint()
                progress("typing", len(text) // 2)
                time.sleep(4)
                checkpoint()
                progress("exporting", len(text))
                output = BytesIO()
                pdf = PdfWriter(); pdf.add_blank_page(width=612, height=792); pdf.write(output)
                return output.getvalue()

            def close(self):
                return True

        @app.get("/watch/{token}")
        def fake_viewer(token: str):
            for desktop in desktops:
                desktop.viewer.connected.set()
            return HTMLResponse("<html><body><h1>Simulated Writer desktop for browser test</h1></body></html>")

        manager = WriterManager(lambda: Session(engine), FakeWriter)
        app.dependency_overrides[get_writer_manager] = lambda: manager
        from contextlib import asynccontextmanager
        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def fake_writer_lifespan(application):
            try:
                async with original_lifespan(application):
                    yield
            finally:
                manager.shutdown()

        app.router.lifespan_context = fake_writer_lifespan
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["SMOKE_API_PORT"]), log_level="warning")


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def wait_server(url, process):
    import httpx
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("A smoke server exited early; inspect the ignored smoke logs.")
        try:
            if httpx.get(url, timeout=1).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError("Smoke server did not become ready within 60 seconds.")


def run_browser(origin, artifacts, live_writer=False, writer_stress=False):
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1512, "height": 1100})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin)
        expect(page).to_have_url(origin + "/jobs")
        page.get_by_label("Upload resume", exact=True).set_input_files({"name": "fictional-resume.txt", "mimeType": "text/plain", "buffer": RESUME.encode()})
        expect(page.get_by_role("heading", name="55 jobs", exact=True)).to_be_visible()
        expect(page.locator("article")).to_have_count(50)
        page.get_by_label("Looking for", exact=True).fill("designer")
        page.get_by_role("button", name="Show more (5 left)", exact=True).click()
        expect(page.locator("article")).to_have_count(55)
        print("PASS: pagination keeps submitted filters while the form is edited", flush=True)
        page.get_by_role("button", name="Search jobs", exact=True).click()
        expect(page.get_by_role("heading", name="0 jobs", exact=True)).to_be_visible()
        page.get_by_label("Looking for", exact=True).fill("ai engineer")
        page.get_by_role("button", name="Search jobs", exact=True).click()
        expect(page.locator("article")).to_have_count(50)
        page.get_by_role("button", name="Details ▾", exact=True).first.click()
        expect(page.get_by_text("All locations", exact=True)).to_be_visible()
        checks = page.get_by_role("checkbox", name="Pick AI Engineer at Fictional Co")
        for index in range(3):
            checks.nth(index).check()
            expect(page.get_by_role("heading", name=f"Your picks ({index + 1} of 3)")).to_be_visible()
        expect(checks.nth(3)).to_be_disabled()
        checks.nth(2).uncheck()
        if live_writer:
            checks.nth(1).uncheck()
        picks_count = 1 if live_writer else 2
        expect(page.get_by_role("link", name=f"Write cover letters ({picks_count})")).to_be_visible()
        page.screenshot(path=str(artifacts / "desktop-search.png"), full_page=True)
        page.get_by_role("link", name=f"Write cover letters ({picks_count})").click()
        page.get_by_label("Your full name", exact=True).fill("Alex Example")
        if not live_writer:
            page.get_by_label("Company context", exact=False).first.fill("simulate failure")
        page.get_by_role("button", name="Preview redacted inputs →", exact=True).click()
        expect(page.get_by_role("heading", name="2. Review what will be sent", exact=True)).to_be_visible()
        preview = page.locator("pre").first
        expect(preview).not_to_contain_text("Alex")
        expect(preview).not_to_contain_text("example.com")
        generate_name = f"Draft {picks_count} {'letter' if picks_count == 1 else 'letters'} live →"
        generate = page.get_by_role("button", name=generate_name, exact=True)
        expect(generate).to_be_disabled()
        page.reload()
        expect(page.get_by_role("button", name=generate_name, exact=True)).to_be_disabled()
        page.get_by_role("checkbox", name="I reviewed these inputs").check()
        page.get_by_role("button", name=generate_name, exact=True).click()

        def watch_draft(*, fails=False, reconnect=False):
            begin_draft = page.get_by_role("button", name="Start drafting", exact=True)
            expect(begin_draft).to_be_enabled(timeout=120000)
            expect(page.get_by_label("Letter text", exact=True)).to_have_count(0)
            expect(page.get_by_role("link", name="Download Writer PDF ↓", exact=True)).to_have_count(0)
            frame = page.frame_locator('iframe[title="Live E2B Writer desktop"]')
            expect(frame.locator("canvas") if live_writer else frame.get_by_text("Simulated Writer desktop for browser test", exact=True)).to_be_visible(timeout=30000)
            if reconnect:
                page.reload()
                expect(page.frame_locator('iframe[title="Live E2B Writer desktop"]').locator("canvas")).to_be_visible(timeout=30000)
                expect(page.get_by_role("button", name="Start drafting", exact=True)).to_be_enabled(timeout=30000)
            page.screenshot(path=str(artifacts / "draft-before.png"), full_page=True)
            params = dict(parse_qsl(urlsplit(page.url).query))
            letter = page.request.get(origin + "/api/jobs/letters/" + params["letter"]).json()
            assert letter["status"] == "generating" and not letter["text"]
            row = page.request.get(origin + "/api/jobs/letters/" + letter["id"] + "/writer").json()["export"]
            assert row["purpose"] == "draft" and not row["pdf_ready"]
            page.get_by_role("button", name="Start drafting", exact=True).click()
            if fails:
                expect(page.get_by_role("button", name="Fictional Co").filter(has_text="Needs retry")).to_have_count(1, timeout=15000)
                return
            progress = page.get_by_role("progressbar", name="Draft characters typed", exact=True)
            expect(progress).to_be_visible(timeout=30000)
            expect(progress).not_to_have_attribute("value", "0", timeout=30000)
            page.screenshot(path=str(artifacts / "draft-live.png"), full_page=True)
            expect(page.get_by_label("Letter text", exact=True)).to_be_visible(timeout=180000)
            if live_writer:
                draft = page.request.get(origin + "/api/jobs/letters/" + letter["id"]).json()
                assert draft["status"] == "draft" and "[NAME]" in draft["text"]
                row = page.request.get(origin + "/api/jobs/letters/" + letter["id"] + "/writer").json()["export"]
                assert row["status"] == "saved" and row["cleanup_confirmed"]
                assert page.request.get(origin + "/api/jobs/writer-exports/" + row["id"] + "/pdf").status == 409
                (artifacts / "draft-metrics.json").write_text(json.dumps({key: row[key] for key in ("purpose", "status", "diagnostics", "cleanup_confirmed", "characters_typed", "total_characters")}, indent=2))
                if writer_stress:
                    from zipfile import ZipFile
                    from xml.etree import ElementTree as ET
                    from crescendo_agent.writer_support import compare_text
                    (artifacts / "fictional-draft.txt").write_text(draft["text"])
                    for suffix in ("odt", "pdf"):
                        shutil.copyfile(artifacts / f"writer-raw.{suffix}", artifacts / f"draft-raw.{suffix}")
                    with ZipFile(artifacts / "draft-raw.odt") as archive:
                        tree = ET.fromstring(archive.read("content.xml"))
                    paragraphs = tree.findall(".//{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p")
                    actual = "\n".join("".join(p.itertext()) for p in paragraphs)
                    assert compare_text(draft["text"], actual)["exact"]
            print("PASS: desktop shown before model drafting, draft typed before review/approval", flush=True)

        watch_draft(fails=not live_writer, reconnect=live_writer)
        retry = page.get_by_role("button", name="Continue / retry drafting", exact=True)
        if not live_writer:
            watch_draft()
            expect(retry).to_be_enabled(timeout=15000)
            retry.click()
            watch_draft()
        expect(page.get_by_role("button", name="Fictional Co").filter(has_text="Review draft")).to_have_count(picks_count)
        editor = page.get_by_label("Letter text", exact=True)
        assert "[NAME]" in editor.input_value()
        if not writer_stress:
            page.locator("summary").filter(has_text="My Python pipeline work").click()
            expect(page.get_by_text("Additional source: posting · Quote found", exact=True)).to_be_visible()
            expect(page.get_by_text("Review the connection against all quoted sources; quote matches do not verify the argument or a proposed contribution.", exact=True)).to_be_visible()
            page.screenshot(path=str(artifacts / "connected-evidence.png"), full_page=True)
            print("PASS: connected sentence displays both resume and company evidence", flush=True)
        editor.fill(editor.input_value().replace("Sincerely,", "Thank you for your time.\n\nSincerely,"))
        page.get_by_role("button", name="Save draft", exact=True).click()
        expect(page.get_by_text("Draft saved.", exact=True)).to_be_visible()
        page.get_by_role("checkbox", name="I reviewed this text and its source flags.", exact=True).check()
        page.get_by_role("button", name="Approve & save", exact=True).click()
        download = page.get_by_role("link", name="Download .txt ↓", exact=True)
        expect(download).to_be_visible()
        with page.expect_download() as downloaded:
            download.click()
        saved = artifacts / "fictional-approved-letter.txt"
        downloaded.value.save_as(saved)
        assert saved.read_text().endswith("Alex Example")
        assert "[NAME]" not in saved.read_text()
        page.reload()
        expect(page.get_by_role("link", name="Download .txt ↓", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Letter & sources", exact=True)).to_have_attribute("aria-pressed", "true")
        expect(page.get_by_label("Letter text", exact=True)).to_be_visible()
        page.screenshot(path=str(artifacts / "desktop-letter.png"), full_page=True)
        with page.expect_popup() as popup:
            page.get_by_role("link", name="Print / save PDF ↗", exact=True).click()
        print_page = popup.value
        expect(print_page.get_by_role("button", name="Print / save as PDF", exact=True)).to_be_enabled()
        print_page.emulate_media(media="print")
        print_page.pdf(path=str(artifacts / "fictional-approved-letter.pdf"), format="Letter")
        print_page.close()
        print("PASS: consent, partial failure/retry, source review, edits, approval, text/PDF, reload", flush=True)
        page.get_by_role("button", name="Live desktop", exact=True).click()
        page.get_by_role("button", name="Open live Writer →", exact=True).click()
        begin = page.get_by_role("button", name="Start typing", exact=True)
        expect(begin).to_be_enabled(timeout=120000)
        live_frame = page.frame_locator('iframe[title="Live E2B Writer desktop"]')
        if live_writer:
            expect(live_frame.locator("canvas")).to_be_visible(timeout=30000)
        else:
            expect(live_frame.get_by_text("Simulated Writer desktop for browser test", exact=True)).to_be_visible()
        page.locator('iframe[title="Live E2B Writer desktop"]').screenshot(path=str(artifacts / "writer-before.png"))
        page.reload()
        if live_writer:
            expect(page.frame_locator('iframe[title="Live E2B Writer desktop"]').locator("canvas")).to_be_visible(timeout=30000)
        expect(page.get_by_role("button", name="Start typing", exact=True)).to_be_enabled(timeout=30000)
        if not live_writer:
            # A poll must not immediately hide an action's failure (live reconnect bug).
            page.route("**/api/jobs/writer-exports/*/begin", lambda route: route.fulfill(
                status=409, json={"detail": "Controlled viewer reconnect. Wait and retry."}), times=1)
            page.get_by_role("button", name="Start typing", exact=True).click()
            expect(page.get_by_text("Controlled viewer reconnect. Wait and retry.", exact=False)).to_be_visible()
            page.wait_for_timeout(2000)
            expect(page.get_by_text("Controlled viewer reconnect. Wait and retry.", exact=False)).to_be_visible()
        page.get_by_role("button", name="Start typing", exact=True).click()
        progress = page.get_by_role("progressbar", name="Approved letter characters typed", exact=True)
        expect(progress).to_be_visible(timeout=30000)
        expect(progress).not_to_have_attribute("value", "0", timeout=30000)
        expect(page.get_by_label("Letter text", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Letter & sources", exact=False).click()
        expect(page.get_by_label("Letter text", exact=True)).to_be_visible()
        expect(page.get_by_label("Letter text", exact=True)).to_be_disabled()
        page.get_by_role("button", name="Live desktop", exact=True).click()
        expect(page.locator('iframe[title="Live E2B Writer desktop"]')).to_be_visible()
        if not live_writer:
            page.get_by_role("button", name="Expand desktop", exact=True).click()
            page.wait_for_function("document.fullscreenElement !== null")
            page.get_by_role("button", name="Exit full screen", exact=True).click()
        page.locator('iframe[title="Live E2B Writer desktop"]').screenshot(path=str(artifacts / "writer-typing.png"))
        print("PASS: Writer opened, viewer reconnected after reload, explicit start, persisted progress, edit protection", flush=True)
        writer_pdf = page.get_by_role("link", name="Download Writer PDF ↓", exact=True)
        params = dict(parse_qsl(urlsplit(page.url).query))
        data = page.request.get(origin + "/api/jobs/letter-sessions/" + params["session"]).json()
        selected_letter = next((l for l in data["letters"] if l["id"] == params.get("letter")), data["letters"][0])
        export_path = origin + "/api/jobs/letters/" + selected_letter["id"] + "/writer"
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            export = page.request.get(export_path).json()["export"]
            if export["status"] in ("saved", "failed", "cancelled", "interrupted"):
                break
            page.wait_for_timeout(300)
        (artifacts / "export-metrics.json").write_text(json.dumps({key: export.get(key) for key in ("status", "characters_typed", "total_characters", "cleanup_confirmed", "diagnostics", "error")}, indent=2))
        if export["status"] != "saved":
            raise RuntimeError("Fictional Writer export failed: " + str(export.get("error")))
        expect(writer_pdf).to_be_visible(timeout=180000)
        with page.expect_download() as exported:
            writer_pdf.click()
        exported.value.save_as(artifacts / "writer-export.pdf")
        if live_writer:
            from pypdf import PdfReader
            from crescendo_agent.writer_support import pdf_words_match
            extracted = "\n".join(p.extract_text() or "" for p in PdfReader(artifacts / "writer-export.pdf").pages)
            assert pdf_words_match(saved.read_text(), extracted)
        expect(page.get_by_text("Text verified · desktop closed", exact=True)).to_be_visible()
        # Use the saved session to find the selected letter without logging its text.
        export = page.request.get(origin + "/api/jobs/letters/" + selected_letter["id"] + "/writer").json()["export"]
        (artifacts / "export-metrics.json").write_text(json.dumps({key: export.get(key) for key in ("status", "characters_typed", "total_characters", "cleanup_confirmed", "diagnostics")}, indent=2))
        page.reload()
        page.get_by_role("button", name="Live desktop", exact=True).click()
        expect(page.get_by_role("link", name="Download Writer PDF ↓", exact=True)).to_be_visible()
        page.screenshot(path=str(artifacts / "writer-saved.png"), full_page=True)
        print("PASS: Writer PDF downloaded, cleanup recorded, result survives reload" + ("; real PDF text matches approved text" if live_writer else " (simulated desktop)"), flush=True)
        assert page.request.post(origin + "/api/jobs/letter-sessions", headers={"Origin": "http://untrusted.example"}, data={}).status == 403
        assert page.request.post(origin + "/api/jobs/letters/not-a-uuid/generate", headers={"Origin": origin}).status == 404
        assert page.request.post(origin + "/api/jobs/writer-exports/not-a-uuid/begin", headers={"Origin": origin}).status == 404
        assert page.request.post(origin + "/api/jobs/writer-exports/00000000-0000-4000-8000-000000000000/cancel", headers={"Origin": "http://untrusted.example"}).status == 403
        page.get_by_role("link", name="Cover letters", exact=True).click()
        expect(page.get_by_role("link", name="Approved Fictional Co")).to_have_count(1)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(origin + "/jobs")
        expect(page.get_by_role("link", name=f"Write cover letters ({picks_count})")).to_be_visible()
        expect(page.get_by_role("link", name="Job search", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(artifacts / "mobile-search.png"))
        # Keep a pagination response pending, remove the resume, then deliver the old result.
        held = []
        page.route("**/api/jobs/search?**offset=50**", lambda route: held.append(route))
        page.get_by_role("button", name="Show more (5 left)", exact=True).click()
        expect(page.get_by_role("button", name="Loading…", exact=True)).to_be_visible()
        page.get_by_role("button", name="Remove", exact=True).click()
        expect(page.get_by_text("Upload your resume to see ranked jobs.", exact=True)).to_be_visible()
        assert held
        held[0].fulfill(status=200, json={"results": [{"title": "STALE SHOULD NEVER RENDER"}]})
        expect(page.locator("article")).to_have_count(0)
        page.wait_for_timeout(300)
        assert "STALE SHOULD NEVER RENDER" not in page.content()
        assert not errors, errors
        print("PASS: saved library, origin/UUID guards, mobile layout, stale response after removal", flush=True)
        browser.close()


def main(live_writer=False, writer_stress=False):
    import sys
    api_port, web_port = free_port(), free_port()
    artifacts = ROOT / ".demo-artifacts" / ("writer-performance-live" if live_writer and writer_stress else "writer-live-smoke" if live_writer else "job-search-smoke")
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="crescendo-job-smoke-") as directory:
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{directory}/smoke.db",
               "DEV_API_TOKEN": secrets.token_urlsafe(40), "GROQ_API_KEY": "fake-never-sent",
               "API_BASE_URL": f"http://127.0.0.1:{api_port}", "SMOKE_API_PORT": str(api_port),
               "NEXT_TELEMETRY_DISABLED": "1", "SMOKE_REAL_WRITER": "1" if live_writer else "0",
               "E2B_API_KEY": "fake-never-sent", "SMOKE_WRITER_STRESS": "1" if writer_stress else "0",
               "SMOKE_WRITER_ARTIFACTS": str(artifacts)}
        if live_writer:
            from crescendo_api.config import get_settings
            key = get_settings().e2b_api_key
            if not key:
                raise RuntimeError("Set E2B_API_KEY before running --live-writer.")
            env["E2B_API_KEY"] = key.get_secret_value()
        # Don't share Next's dev lock, generated files, or local environment files
        # with the user's running app. Dependencies are reused, source is copied.
        web_copy = Path(directory) / "web"
        shutil.copytree(ROOT / "apps/web", web_copy,
            ignore=shutil.ignore_patterns("node_modules", ".next", ".env*", "tsconfig.tsbuildinfo"))
        (web_copy / "node_modules").symlink_to(ROOT / "apps/web/node_modules", target_is_directory=True)
        with (artifacts / "api.log").open("w") as api_log, (artifacts / "web.log").open("w") as web_log:
            api_process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve"], cwd=ROOT, env=env, stdout=api_log, stderr=subprocess.STDOUT)
            web_process = None
            try:
                wait_server(f"http://127.0.0.1:{api_port}/health", api_process)
                web_process = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(web_port)], cwd=web_copy, env=env, stdout=web_log, stderr=subprocess.STDOUT, start_new_session=True)
                origin = f"http://127.0.0.1:{web_port}"
                wait_server(origin + "/jobs", web_process)
                run_browser(origin, artifacts, live_writer, writer_stress)
            finally:
                import signal
                if web_process is not None:
                    os.killpg(web_process.pid, signal.SIGTERM)
                    web_process.wait(timeout=10)
                api_process.terminate()
                api_process.wait(timeout=10)
    print("PASS: isolated browser smoke (real E2B, fictional letter, fake Groq)" if live_writer else "PASS: isolated job-search/Writer browser smoke (fake providers only)", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--live-writer", action="store_true", help="Use real E2B for a fictional approved letter; Groq stays fake.")
    parser.add_argument("--writer-stress", action="store_true", help="Use a full-length fictional letter with Unicode punctuation.")
    args = parser.parse_args()
    serve() if args.serve else main(args.live_writer, args.writer_stress)
