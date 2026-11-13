"""Real Groq decisions and real Wikipedia browsing inside a temporary E2B desktop."""
import os

from crescendo_agent.e2b_desktop import open_e2b_desktop
from crescendo_agent.groq_model import GroqModel
from crescendo_agent.loop import run_agent
from crescendo_security.policy import TaskGrant


def main():
    for name in ("GROQ_API_KEY", "E2B_API_KEY"):
        if not os.environ.get(name):
            raise SystemExit(f"Set {name} in your shell first.")
    wiki = "https://en.wikipedia.org/wiki/Boston"
    grant = TaskGrant("groq-e2b-demo", frozenset({"navigate", "finish"}),
                      frozenset({"en.wikipedia.org"}))
    model = GroqModel(os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"))
    with open_e2b_desktop(grant) as desktop:
        result = run_agent(
            f"Read {wiki} and tell me the capital of Massachusetts. Cite your source.",
            grant, desktop, model, max_steps=5, deadline_seconds=120,
        )
        print("Status:", result.status)
        print("Answer:", result.answer)
        print("Sources:", result.sources)
        print("Visited:", desktop.visited)
        print("Denied tool calls:", len(result.denied))
        print("Blocked browser requests:", len(desktop.blocked_requests))


if __name__ == "__main__":
    main()
