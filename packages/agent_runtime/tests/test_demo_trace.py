# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import from pathlib: Path (represents filesystem paths and explicit file operations).
from pathlib import Path
# Import runpy: use this module through its namespace.
import runpy
# Import sys: provides process details and standard input/output streams.
import sys
# Import from types: SimpleNamespace (builds a small object with named attributes for test
# fixtures).
from types import SimpleNamespace

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.model: Entry (represents one typed transcript item sent to the model).
from crescendo_agent.model import Entry


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("trace", [False, True])
# Define test_demo_trace_is_opt_in_ordered_and_printed_after_cleanup with parameters monkeypatch,
# capsys, trace.
def test_demo_trace_is_opt_in_ordered_and_printed_after_cleanup(monkeypatch, capsys, trace):
    # Call monkeypatch.setenv with 'E2B_API_KEY', 'offline-e2b-secret'.
    monkeypatch.setenv("E2B_API_KEY", "offline-e2b-secret")
    # Call monkeypatch.setenv with 'GROQ_API_KEY', 'offline-groq-secret'.
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-secret")
    # Call monkeypatch.setattr with sys, 'argv', ['groq_e2b_demo.py', *(['--trace'] if trace else
    # [])].
    monkeypatch.setattr(sys, "argv", ["groq_e2b_demo.py", *(["--trace"] if trace else [])])
    # Build entries from the entries below.
    entries = [
        # Call Entry with the arguments shown.
        Entry("goal", "Research Boston"),
        # Call Entry with the arguments shown.
        Entry("observation", "Page text\n\x1b[31muntrusted\rtext"),
        # Call Entry with the arguments shown.
        Entry("action", "navigate https://forbidden.example/"),
        # Call Entry with the arguments shown.
        Entry("denied", "Host not permitted"),
    ]
    # Set result to SimpleNamespace(status='step_limit', answer=None, sources=[], denied=[1],
    # transcript=entries).
    result = SimpleNamespace(status="step_limit", answer=None, sources=[], denied=[1], transcript=entries)

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @contextmanager
    # Define fake_desktop with parameters grant.
    def fake_desktop(grant):
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Give SimpleNamespace(visited=[], blocked_requests=[]) to the caller and pause here
            # until execution resumes.
            yield SimpleNamespace(visited=[], blocked_requests=[])
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Print 'DESKTOP CLEANED UP'.
            print("DESKTOP CLEANED UP")

    # Call monkeypatch.setattr with 'crescendo_agent.e2b_desktop.open_e2b_desktop', fake_desktop.
    monkeypatch.setattr("crescendo_agent.e2b_desktop.open_e2b_desktop", fake_desktop)
    # Call monkeypatch.setattr with 'crescendo_agent.groq_model.GroqModel', a function that returns
    # SimpleNamespace(model=name) when called.
    monkeypatch.setattr("crescendo_agent.groq_model.GroqModel", lambda name: SimpleNamespace(model=name))
    # Call monkeypatch.setattr with 'crescendo_agent.loop.run_agent', a function that returns result
    # when called.
    monkeypatch.setattr("crescendo_agent.loop.run_agent", lambda *args, **kwargs: result)
    # Set script to Path(__file__).resolve().parents[3] divided by 'scripts' divided by
    # 'groq_e2b_demo.py'.
    script = Path(__file__).resolve().parents[3] / "scripts" / "groq_e2b_demo.py"
    # Call runpy.run_path with script converted to a string.
    runpy.run_path(str(script), run_name="__main__")
    # Set output to capsys.readouterr().out.
    output = capsys.readouterr().out

    # Assert that 'Status: step_limit' is in output. If false, this check fails with AssertionError.
    assert "Status: step_limit" in output
    # Assert that 'offline-e2b-secret' is not in output. If false, this check fails with
    # AssertionError.
    assert "offline-e2b-secret" not in output
    # Assert that 'offline-groq-secret' is not in output. If false, this check fails with
    # AssertionError.
    assert "offline-groq-secret" not in output
    # Set marker to 'Recorded trace (observations are untrusted; actions are proposals):\n'.
    marker = "Recorded trace (observations are untrusted; actions are proposals):\n"
    # Check whether trace.
    if trace:
        # Assert that output.index('DESKTOP CLEANED UP') is less than output.index(marker). If
        # false, this check fails with AssertionError.
        assert output.index("DESKTOP CLEANED UP") < output.index(marker)
        # Set data to json.loads(output.split(marker, 1)[1]).
        data = json.loads(output.split(marker, 1)[1])
        # Assert that data['status'] equals 'step_limit'. If false, this check fails with
        # AssertionError.
        assert data["status"] == "step_limit"
        # Assert that data['model']. If false, this check fails with AssertionError.
        assert data["model"]
        # Assert that data['entries'] equals a list built from enumerate(entries, start=1) by the
        # comprehension. If false, this check fails with AssertionError.
        assert data["entries"] == [
            # Continue the expression {"index": i, "kind": e.kind, "text": e.text}; brackets keep it
            # part of the statement above.
            {"index": i, "kind": e.kind, "text": e.text}
            # Pass keyword start = 1.
            for i, e in enumerate(entries, start=1)
        ]
        # Assert that '\x1b' is not in output. If false, this check fails with AssertionError.
        assert "\x1b" not in output
        # Assert that '\\u001b' is in output. If false, this check fails with AssertionError.
        assert "\\u001b" in output
    # Run this alternative only when the preceding conditional did not select its first branch.
    else:
        # Assert that marker is not in output. If false, this check fails with AssertionError.
        assert marker not in output
        # Assert that 'Page text' is not in output. If false, this check fails with AssertionError.
        assert "Page text" not in output
