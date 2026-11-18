"""Isolated browser check for "Why [company]?" answers: research -> consent -> agent turns -> copy.

Run .venv/bin/python scripts/smoke_why_company.py from the repository root.
Real Next.js/FastAPI/SQLite with fictional data. The researcher and the drafting
model are fakes at their paid boundaries; no Groq request is made. The resume and
pick are seeded directly so this check does not depend on the job-search UI.
"""
import argparse
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_job_search import free_port, wait_server  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POSTING_ID = "00000000-0000-4000-8000-000000000042"
RESUME = "Alex Example\nalex@example.com\nBuilt Python data pipelines for 3 years. Reduced latency by 25%."
FACT = {"topic": "product", "claim": "Fictional Co builds a profiler for developers.",
        "quote": "Our profiler shows developers where their code spends time.", "url": "https://fictional.example/about"}


def serve():
    from datetime import datetime, timezone
    import uvicorn
    from sqlalchemy.orm import Session
    from crescendo_api.database import get_engine
    from crescendo_api.letters import Draft, check_draft
    from crescendo_api.main import app
    from crescendo_api.models import Base, JobPick, JobPosting, JobResume
    from crescendo_api.routes.letters import company_researcher, draft_generator

    now = datetime.now(timezone.utc)
    engine = get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(JobPosting(source="ashby", posting_id=POSTING_ID, company_slug="fictional", company_name="Fictional Co",
                               title="AI Engineer", url=f"https://jobs.ashbyhq.com/fictional/{POSTING_ID}",
                               description="We build tools for developers. Python required.",
                               countries=["United States"], locations=["New York"], first_seen_at=now, last_seen_at=now))
        session.add(JobResume(id=1, filename="fictional-resume.txt", text=RESUME, skills=["Python"], uploaded_at=now))
        session.add(JobPick(source="ashby", posting_id=POSTING_ID, picked_at=now))
        session.commit()

    def researcher(job, key, model):
        assert "resume" not in job and "Alex" not in str(job)
        time.sleep(0.5)
        return {"status": "done", "model": model, "researched_at": now.isoformat(), "facts": [FACT],
                "excluded": [{**FACT, "quote": "We invented time travel.", "reason": "The quote was not found on the cited page."}],
                "open_questions": ["Team size"]}

    raw = {"paragraphs": [[
        {"text": "Fictional Co's profiler shows developers where their code spends time, and that is the problem I keep choosing.",
         "source": "company_research", "quote": FACT["quote"], "supporting_quotes": []},
        {"text": "I built Python data pipelines for 3 years and reduced latency by 25%, so I know how much a slow path costs a team.",
         "source": "resume", "quote": "Built Python data pipelines for 3 years.",
         "supporting_quotes": [{"source": "resume", "quote": "Reduced latency by 25%."}]},
        {"text": "Your team builds tools for developers, and I want my next work to make that kind of slowness visible to the people fixing it.",
         "source": "posting", "quote": "We build tools for developers.", "supporting_quotes": []}]]}

    def generator(inputs, posting, key, on_turn=None):
        assert posting["company_research"]["facts"] == [FACT]
        turns = []
        for role, summary in [("thinker", "Pair the profiler with latency work."), ("worker", "Drafted 70 words."),
                              ("verifier", "Specific and supported.")]:
            time.sleep(1.2)
            turns.append({"turn": len(turns) + 1, "role": role, "status": "done", "seconds": 1.2, "summary": summary,
                          "detail": {"accepted": True} if role == "verifier" else {}})
            on_turn(list(turns))
        text, checks = check_draft(Draft.model_validate(raw), inputs["resume"], posting)
        checks.append({"text": "The Verifier accepted this answer on turn 3.", "source": "verifier", "quote": "",
                       "quote_found": False, "supporting_quotes": [], "flags": []})
        return text, checks

    app.dependency_overrides[company_researcher] = lambda: researcher
    app.dependency_overrides[draft_generator] = lambda: generator
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ["SMOKE_API_PORT"]), log_level="warning")


def run_browser(origin, artifacts):
    from playwright.sync_api import expect, sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 1000}, permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin + "/jobs/letters?new=1")
        page.get_by_label("Your full name").fill("Alex Example")
        page.get_by_role("button", name="Preview redacted inputs →", exact=True).click()
        expect(page.get_by_role("heading", name="2. Research the companies, then review what will be sent")).to_be_visible()
        draft = page.get_by_role("button", name="Draft 1 answer →", exact=True)
        page.get_by_role("checkbox", name="I reviewed these inputs").check()
        page.get_by_role("button", name="Research companies", exact=True).click()
        expect(page.get_by_text(FACT["quote"], exact=True)).to_be_visible()
        expect(page.get_by_role("link", name="fictional.example ↗")).to_be_visible()
        # Research changed the inputs, so the earlier consent is cleared.
        expect(page.get_by_role("checkbox", name="I reviewed these inputs")).not_to_be_checked()
        expect(draft).to_be_disabled()
        page.screenshot(path=str(artifacts / "research.png"), full_page=True)
        print("PASS: research shows verified facts and resets consent", flush=True)

        page.get_by_role("checkbox", name="I reviewed these inputs").check()
        draft.click()
        expect(page.get_by_text("Thinker · plan", exact=True)).to_be_visible(timeout=10000)
        page.screenshot(path=str(artifacts / "turns-live.png"), full_page=True)
        expect(page.get_by_role("heading", name="Why Fictional Co?")).to_be_visible()
        answer = page.get_by_label("Answer", exact=True)
        expect(answer).to_have_value(__import__("re").compile("^Fictional Co's profiler"), timeout=15000)
        text = answer.input_value()
        assert not text.startswith("Dear") and "Sincerely" not in text and "[NAME]" not in text
        expect(page.get_by_role("button", name="Live desktop")).to_have_count(0)
        expect(page.get_by_role("link", name="Print / save PDF ↗")).to_have_count(0)
        print("PASS: three agent turns shown while drafting; answer has no greeting/signature; no PDF/desktop", flush=True)

        page.get_by_role("button", name="Copy answer", exact=True).click()
        expect(page.get_by_role("button", name="Copied ✓", exact=True)).to_be_visible()
        assert page.evaluate("navigator.clipboard.readText()") == text
        page.get_by_text("How this answer was made (3 agent turns)").click()
        expect(page.get_by_text("Specific and supported.")).to_be_visible()
        page.get_by_role("checkbox", name="I reviewed this text and its source flags.").check()
        page.get_by_role("button", name="Mark ready", exact=True).click()
        expect(page.get_by_text("Marked ready and saved.")).to_be_visible()
        page.screenshot(path=str(artifacts / "answer.png"), full_page=True)
        page.reload()
        expect(page.get_by_label("Answer", exact=True)).to_have_value(text)
        assert not errors, errors
        print("PASS: copy puts the exact answer on the clipboard; ready state survives reload", flush=True)
        browser.close()


def main():
    api_port, web_port = free_port(), free_port()
    artifacts = ROOT / ".demo-artifacts" / "why-company-smoke"
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="crescendo-why-smoke-") as directory:
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{directory}/smoke.db",
               "DEV_API_TOKEN": secrets.token_urlsafe(40), "GROQ_API_KEY": "fake-never-sent",
               "API_BASE_URL": f"http://127.0.0.1:{api_port}", "SMOKE_API_PORT": str(api_port),
               "NEXT_TELEMETRY_DISABLED": "1"}
        web_copy = Path(directory) / "web"
        shutil.copytree(ROOT / "apps/web", web_copy,
                        ignore=shutil.ignore_patterns("node_modules", ".next", ".env*", "tsconfig.tsbuildinfo"))
        (web_copy / "node_modules").symlink_to(ROOT / "apps/web/node_modules", target_is_directory=True)
        with (artifacts / "api.log").open("w") as api_log, (artifacts / "web.log").open("w") as web_log:
            api = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve"], cwd=ROOT, env=env,
                                   stdout=api_log, stderr=subprocess.STDOUT)
            web = None
            try:
                wait_server(f"http://127.0.0.1:{api_port}/health", api)
                web = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(web_port)], cwd=web_copy, env=env,
                                       stdout=web_log, stderr=subprocess.STDOUT, start_new_session=True)
                origin = f"http://127.0.0.1:{web_port}"
                wait_server(origin + "/jobs", web)
                run_browser(origin, artifacts)
            finally:
                import signal
                if web is not None:
                    os.killpg(web.pid, signal.SIGTERM)
                    web.wait(timeout=10)
                api.terminate()
                api.wait(timeout=10)
    print("PASS: isolated why-company browser smoke (fake providers only)", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    serve() if parser.parse_args().serve else main()
