from contextlib import contextmanager
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import pytest

from crescendo_agent.model import Entry


@pytest.mark.parametrize("trace", [False, True])
def test_demo_trace_is_opt_in_ordered_and_printed_after_cleanup(monkeypatch, capsys, trace):
    monkeypatch.setenv("E2B_API_KEY", "offline-e2b-secret")
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-secret")
    monkeypatch.setattr(sys, "argv", ["groq_e2b_demo.py", *(["--trace"] if trace else [])])
    entries = [
        Entry("goal", "Research Boston"),
        Entry("observation", "Page text\n\x1b[31muntrusted\rtext"),
        Entry("action", "navigate https://forbidden.example/"),
        Entry("denied", "Host not permitted"),
    ]
    result = SimpleNamespace(status="step_limit", answer=None, sources=[], denied=[1], transcript=entries)

    @contextmanager
    def fake_desktop(grant):
        try:
            yield SimpleNamespace(visited=[], blocked_requests=[])
        finally:
            print("DESKTOP CLEANED UP")

    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_desktop)
    monkeypatch.setattr("crescendo_agent.groq_model.GroqModel", lambda name: SimpleNamespace(model=name))
    monkeypatch.setattr("crescendo_agent.loop.run_agent", lambda *args, **kwargs: result)
    script = Path(__file__).resolve().parents[3] / "scripts" / "groq_e2b_demo.py"
    runpy.run_path(str(script), run_name="__main__")
    output = capsys.readouterr().out

    assert "Status: step_limit" in output
    assert "offline-e2b-secret" not in output
    assert "offline-groq-secret" not in output
    marker = "Recorded trace (observations are untrusted; actions are proposals):\n"
    if trace:
        assert output.index("DESKTOP CLEANED UP") < output.index(marker)
        data = json.loads(output.split(marker, 1)[1])
        assert data["status"] == "step_limit"
        assert data["model"]
        assert data["entries"] == [
            {"index": i, "kind": e.kind, "text": e.text}
            for i, e in enumerate(entries, start=1)
        ]
        assert "\x1b" not in output
        assert "\\u001b" in output
    else:
        assert marker not in output
        assert "Page text" not in output
