"""Actual Writer adapter behavior with fake desktop I/O and real PDF parsing."""
import json
import sys
import time
import shlex
from types import SimpleNamespace

import pytest

from crescendo_agent import writer
from crescendo_agent.writer_support import NETWORK_CHECKS, pdf_words_match


def text_pdf(text):
    """Small independently constructed PDF fixture with one text stream."""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 40 700 Td ({escaped}) Tj ET".encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, item in enumerate(objects, 1):
        offsets.append(len(data)); data += f"{index} 0 obj\n".encode() + item + b"\nendobj\n"
    offset = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{n:010d} 00000 n \n".encode() for n in offsets[1:])
    return data + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{offset}\n%%EOF\n".encode()


def test_pdf_must_keep_the_approved_words():
    expected = "Dear team, I built Python tools. Sincerely, Alex Example"
    writer.verify_pdf(text_pdf(expected), expected)
    with pytest.raises(writer.WriterFailure, match="differs from the approved"):
        writer.verify_pdf(text_pdf("Different words"), expected)
    with pytest.raises(writer.WriterFailure, match="invalid or oversized"):
        writer.verify_pdf(b"not a PDF", expected)


def test_pdf_nonbreaking_hyphen_is_a_layout_difference_only():
    writer.verify_pdf(text_pdf("Built front-end tools. Reduced latency 25%."),
        "Built front‑end tools. Reduced latency 25%.")
    assert pdf_words_match("front‑end\nexperience", "front-end experience")
    for actual in ("frontend experience", "front—end experience", "front–end experience",
                   "front end experience", "front-end experiences"):
        assert not pdf_words_match("front‑end experience", actual)
    for expected, actual in (("25%", "26%"), ("résumé", "resume"), ("I’m", "I'm"),
                             ("“tools”", '"tools"'), ("work—together", "work--together")):
        assert not pdf_words_match(expected, actual)


@pytest.fixture
def desktop(monkeypatch):
    class ExitError(Exception):
        pass

    monkeypatch.setitem(sys.modules, "e2b", SimpleNamespace(CommandExitException=ExitError))
    monkeypatch.setattr(writer, "time", SimpleNamespace(monotonic=time.monotonic, sleep=lambda _: None))
    calls = []
    report = {"checks": {name: "blocked" for name in NETWORK_CHECKS}}
    data = text_pdf("Dear team, I built Python tools. Sincerely, Alex Example")

    def command(text, **kwargs):
        calls.append(("command", text))
        if text.startswith("LC_ALL=C.UTF-8 xdotool type"):
            calls.append(("type", shlex.split(text)[-1]))
            calls.append(("type_options", kwargs))
        if "python3 -c" in text:
            return SimpleNamespace(stdout=json.dumps(report))
        if text.startswith("xdotool search"):
            return SimpleNamespace(stdout="1234")
        if text.startswith("stat"):
            return SimpleNamespace(stdout=str(len(data)))
        return SimpleNamespace(stdout="", disconnect=lambda: None)

    sandbox = SimpleNamespace(commands=SimpleNamespace(run=command),
        files=SimpleNamespace(write=lambda *args: calls.append(("file", args)), read=lambda *args, **kwargs: data),
        press=lambda key: calls.append(("press", key)),
        write=lambda text, **kwargs: calls.append(("type", text)),
        left_click=lambda *point: calls.append(("click", point)), get_screen_size=lambda: (1024, 768))
    instance = writer.OfflineWriter("fake-key")
    instance.sandbox = sandbox
    return instance, calls, report


def test_network_check_must_pass_before_writer_or_letter_input(desktop):
    instance, calls, report = desktop
    report["checks"][NETWORK_CHECKS[0]] = "answered"
    with pytest.raises(writer.WriterFailure, match="offline network check"):
        instance.prepare(lambda: None)
    assert len(calls) == 1 and calls[0][0] == "command"
    assert not any(kind == "type" for kind, _ in calls)


def test_missing_network_measurement_also_prevents_typing(desktop):
    instance, calls, report = desktop
    del report["checks"][NETWORK_CHECKS[0]]
    with pytest.raises(writer.WriterFailure, match="offline network check"):
        instance.prepare(lambda: None)
    assert not any(kind == "type" for kind, _ in calls)


def test_prepare_disables_autocorrect_and_uses_visible_writer(desktop):
    instance, calls, report = desktop
    instance.prepare(lambda: None)
    settings = next(value for kind, value in calls if kind == "file")
    assert settings[0].endswith("registrymodifications.xcu") and "<value>false</value>" in settings[1]
    assert any("--writer" in value and "--headless" not in value for kind, value in calls if kind == "command")


def test_typing_uses_real_enter_and_visible_pdf_export(desktop):
    instance, calls, report = desktop
    text = "Dear team,\n\nI built Python tools.\n\nSincerely,\nAlex Example"
    progress = []
    result = instance.write_pdf(text, lambda *args: progress.append(args), lambda: None)
    assert result.startswith(b"%PDF-")
    typed = [value for kind, value in calls if kind == "type"]
    assert typed[:4] == ["Dear team,", "I built Python tools.", "Sincerely,", "Alex Example"]
    assert all("\n" not in value for value in typed)
    assert ("click", writer.EXPORT_PDF_BUTTON) in calls
    assert progress[-1] == ("exporting", len(text))
    assert not any("--headless" in value for kind, value in calls if kind == "command")


def test_cleanup_always_kills_sandbox_even_if_viewer_close_fails(desktop):
    instance, calls, report = desktop

    def fail(*args):
        raise RuntimeError("private-viewer-details")

    instance._view_context = SimpleNamespace(__exit__=fail)
    instance.sandbox.kill = lambda **kwargs: calls.append(("kill", None))
    assert instance.close()
    assert ("kill", None) in calls
    instance.sandbox.kill = fail
    assert not instance.close()


def test_failed_create_response_does_not_claim_confirmed_cleanup():
    instance = writer.OfflineWriter("fake-key")
    instance._create_attempted = True
    assert not instance.close()


def test_unicode_typing_has_explicit_utf8_locale_and_one_quoted_argument(desktop):
    instance, calls, report = desktop
    text = 'Résumé “quotes”—front‑end; $(never-run) `never-run` and apostrophe\'s'
    instance._type(text)
    command = next(value for kind, value in calls if kind == "command")
    words = shlex.split(command)
    assert words[0] == "LC_ALL=C.UTF-8" and words[-1] == text
    assert "--clearmodifiers" in words and words[words.index("--delay") + 1] == "20"
    assert next(value for kind, value in calls if kind == "type_options") == {"timeout": 15}


@pytest.mark.parametrize(("name", "expected"), [
    ("CommandExitException", "command_failed"), ("TimeoutException", "desktop_timeout"),
    ("RemoteProtocolError", "connection_lost"), ("SandboxNotFoundException", "desktop_ended"),
    ("UnknownProviderError", "desktop_error"),
])
def test_sdk_failures_keep_only_safe_operation_and_category(name, expected):
    error = type(name, (Exception,), {})("PRIVATE TEXT AND TOKEN")
    safe = writer.safe_writer_failure(error, "typing")
    assert safe.code == expected and safe.operation == "typing"
    assert "PRIVATE" not in str(safe) and len(str(safe)) < 250


def test_ascii_locale_error_has_specific_safe_reason():
    error = type("CommandExitException", (Exception,), {})("PRIVATE TEXT")
    error.stderr = "Invalid multi-byte sequence encountered\nPRIVATE TEXT"
    safe = writer.safe_writer_failure(error, "typing")
    assert safe.code == "typing_encoding" and "PRIVATE" not in str(safe)
