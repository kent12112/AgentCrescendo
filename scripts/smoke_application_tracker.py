"""Real browser/API/SQLite tracker check with fictional jobs and no external providers.

Run .venv/bin/python scripts/smoke_application_tracker.py [--build].
Uses a temporary source copy so the user's Next.js development server keeps running.
"""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile

from smoke_job_search import free_port, wait_server

ROOT = Path(__file__).resolve().parents[1]


def serve():
    from datetime import datetime, timezone
    import uvicorn
    from sqlalchemy.orm import Session
    from crescendo_api.database import get_engine
    from crescendo_api.main import app
    from crescendo_api.models import Base, JobPosting

    engine = get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for number in range(55):
            session.add(JobPosting(source="ashby", posting_id=f"00000000-0000-4000-8000-{number:012d}",
                company_slug=f"fixture-{number}", company_name=f"Fictional Co {number}", title="AI Engineer",
                url=f"https://jobs.ashbyhq.com/fixture-{number}/00000000-0000-4000-8000-{number:012d}",
                description="We build developer tools with Python. Three years of experience.",
                countries=["United States"], locations=["New York"], workplace="hybrid",
                published_at=datetime.now(timezone.utc), first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc)))
        session.commit()
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["SMOKE_API_PORT"]))


def run_browser(origin, artifacts, database_url):
    from playwright.sync_api import expect, sync_playwright
    from sqlalchemy import create_engine, delete
    from sqlalchemy.orm import Session
    from crescendo_api.models import JobPosting

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin + "/jobs")
        page.get_by_label("Upload resume", exact=True).set_input_files({"name": "fictional.txt",
            "mimeType": "text/plain", "buffer": b"Alex Example\nBuilt Python tools and LLM applications for 3 years."})
        expect(page.get_by_role("heading", name="55 jobs", exact=True)).to_be_visible()
        expect(page.locator("article")).to_have_count(50)
        expect(page.get_by_label("Max years asked")).not_to_be_visible()
        page.get_by_text("More filters", exact=True).click()
        expect(page.get_by_label("Max years asked")).to_be_visible()
        page.get_by_text("More filters", exact=True).click()
        page.get_by_label("Looking for", exact=True).fill("designer")
        page.get_by_role("button", name="Show more (5 left)", exact=True).click()
        expect(page.locator("article")).to_have_count(55)
        page.get_by_label("Looking for", exact=True).fill("ai engineer")
        page.get_by_role("checkbox", name="Pick AI Engineer at Fictional Co 0", exact=True).check()
        expect(page.get_by_role("link", name="Craft Why-company answers", exact=True)).to_be_visible()
        page.locator("article").first.get_by_role("button", name="Mark applied", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("saved to your application tracker")
        expect(page.locator("article").first.get_by_role("link", name="Applied ·")).to_be_visible()
        page.screenshot(path=str(artifacts / "search-desktop.png"), full_page=True)

        page.get_by_label("Hide applied jobs", exact=True).check()
        page.get_by_role("button", name="Search jobs", exact=True).click()
        expect(page.get_by_role("heading", name="54 jobs", exact=True)).to_be_visible()
        expect(page.locator("article")).to_have_count(50)
        page.get_by_role("button", name="Show more (4 left)", exact=True).click()
        expect(page.locator("article")).to_have_count(54)
        page.reload()
        expect(page.get_by_label("Hide applied jobs", exact=True)).to_be_checked()
        expect(page.get_by_role("heading", name="54 jobs", exact=True)).to_be_visible()
        page.get_by_role("link", name="Applications", exact=True).click()
        expect(page.locator("article")).to_have_count(1)
        page.get_by_text("Update application", exact=True).click()
        form = page.locator("article form")
        form.get_by_label("Status", exact=True).select_option("interviewing")
        form.get_by_label("Applied date", exact=True).fill("2026-11-10")
        form.get_by_label("Follow-up date", exact=True).fill("2026-11-11")
        form.get_by_label("Notes", exact=True).fill("Recruiter chat complete. <script>window.fixtureExecuted=true</script>")
        form.get_by_role("button", name="Save changes", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Saved Fictional Co 0")
        page.reload()
        expect(page.locator("article")).to_contain_text("Interviewing")
        expect(page.locator("article")).to_contain_text("Recruiter chat complete.")
        expect(page.locator("article")).to_contain_text("Follow-up due")
        assert page.evaluate("window.fixtureExecuted") is None
        page.get_by_label("Find an application", exact=True).fill("unmatched")
        expect(page.get_by_text("No applications match these filters.", exact=True)).to_be_visible()
        page.get_by_label("Find an application", exact=True).fill("")
        page.get_by_label("Status", exact=True).select_option("offer")
        expect(page.locator("article")).to_have_count(0)
        page.get_by_label("Status", exact=True).select_option("all")

        # Delete only this temporary fixture's posting; the saved snapshot must still render.
        engine = create_engine(database_url)
        with Session(engine) as session:
            session.execute(delete(JobPosting).where(JobPosting.posting_id == "00000000-0000-4000-8000-000000000000"))
            session.commit()
        engine.dispose()
        page.reload()
        expect(page.locator("article")).to_contain_text("Posting no longer in search")
        page.get_by_text("Saved job description", exact=True).click()
        expect(page.locator("article")).to_contain_text("We build developer tools with Python.")
        page.screenshot(path=str(artifacts / "tracker-desktop.png"), full_page=True)

        headers = {"Origin": "http://untrusted.example", "Content-Type": "application/json"}
        target = origin + "/api/jobs/applications/ashby/00000000-0000-4000-8000-000000000001"
        assert page.request.put(target, data="{}", headers=headers).status == 403
        assert page.request.delete(target + "?version=1", headers=headers).status == 403
        assert page.request.put(target, data="{", headers={"Origin": origin, "Content-Type": "application/json"}).status == 400

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(artifacts / "tracker-mobile.png"), full_page=True)
        page.get_by_text("Update application", exact=True).click()
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Remove from tracker", exact=True).click()
        expect(page.locator("article")).to_have_count(0)
        page.reload()
        expect(page.get_by_role("link", name="Browse Ashby jobs", exact=True)).to_be_visible()
        page.get_by_role("link", name="Find jobs", exact=True).first.click()
        expect(page.get_by_role("heading", name="54 jobs", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(artifacts / "search-mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()


def main(build=False):
    api_port, web_port = free_port(), free_port()
    artifacts = ROOT / ".demo-artifacts/application-tracker-smoke"
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="crescendo-tracker-") as directory:
        database_url = f"sqlite:///{directory}/smoke.db"
        env = {**os.environ, "DATABASE_URL": database_url, "DEV_API_TOKEN": secrets.token_urlsafe(40),
               "API_BASE_URL": f"http://127.0.0.1:{api_port}", "SMOKE_API_PORT": str(api_port),
               "GROQ_API_KEY": "", "E2B_API_KEY": "", "NEXT_TELEMETRY_DISABLED": "1"}
        web_copy = Path(directory) / "web"
        shutil.copytree(ROOT / "apps/web", web_copy,
            ignore=shutil.ignore_patterns("node_modules", ".next", ".env*", "tsconfig.tsbuildinfo"))
        (web_copy / "node_modules").symlink_to(ROOT / "apps/web/node_modules", target_is_directory=True)
        with (artifacts / "api.log").open("w") as api_log, (artifacts / "web.log").open("w") as web_log:
            api_process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve"],
                cwd=ROOT, env=env, stdout=api_log, stderr=subprocess.STDOUT)
            web_process = None
            try:
                wait_server(f"http://127.0.0.1:{api_port}/health", api_process)
                web_process = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(web_port)],
                    cwd=web_copy, env=env, stdout=web_log, stderr=subprocess.STDOUT, start_new_session=True)
                origin = f"http://127.0.0.1:{web_port}"
                wait_server(origin + "/jobs", web_process)
                run_browser(origin, artifacts, database_url)
            finally:
                if web_process is not None:
                    os.killpg(web_process.pid, signal.SIGTERM)
                    web_process.wait(timeout=10)
                api_process.terminate()
                api_process.wait(timeout=10)
        if build:
            with (artifacts / "build.log").open("w") as log:
                subprocess.run(["npm", "run", "build"], cwd=web_copy, env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
    print("PASS: isolated application tracker browser smoke" + (" and production build" if build else ""), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    serve() if args.serve else main(args.build)
