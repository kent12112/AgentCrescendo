"""Real, offline LibreOffice Writer export; no model or personal-source research here."""
from io import BytesIO
import json
import shlex
import time

from .writer_support import (DOC_PATH, PDF_PATH, SCREEN, EXPORT_PDF_BUTTON, WRITER_PROFILE,
    WRITER_SETTINGS_OFF, GUEST_NETWORK_CHECK, network_config, judge_network,
    settings_xcu, typing_plan, looks_like_pdf, pdf_words_match, MAX_PDF_BYTES)

MAX_WRITER_CHARACTERS = 6000
WRITER_LIFETIME = 600
TYPING_CHUNK = 100
TYPING_DELAY_MS = 20


class WriterFailure(Exception):
    """Only fixed, safe messages may leave this adapter."""

    def __init__(self, message: str, *, code="writer_failed", operation=None):
        super().__init__(message)
        self.code = code
        self.operation = operation


def safe_writer_failure(error: Exception, operation: str) -> WriterFailure:
    """SDK command errors can contain the typed text. Read type/status only."""
    name = type(error).__name__
    if isinstance(error, TimeoutError) or name in {"TimeoutException", "ReadTimeout", "ConnectTimeout", "APITimeoutError"}:
        return WriterFailure(f"The desktop timed out during {operation}. Retry on a fresh desktop; the approved letter is kept.", code="desktop_timeout", operation=operation)
    if name in {"CommandExitException", "CommandResult"}:
        if "Invalid multi-byte sequence" in (getattr(error, "stderr", "") or ""):
            return WriterFailure("The desktop keyboard could not read Unicode text. The export stopped; retry on a fresh desktop with UTF-8 typing.", code="typing_encoding", operation=operation)
        return WriterFailure(f"The desktop keyboard command failed during {operation}. The export stopped to avoid duplicating text. Retry on a fresh desktop.", code="command_failed", operation=operation)
    if name in {"SandboxNotFoundException", "NotFoundException"} or getattr(error, "status_code", None) == 404:
        return WriterFailure("The desktop session ended before the PDF was saved. Retry on a fresh desktop.", code="desktop_ended", operation=operation)
    if name in {"ConnectError", "NetworkError", "RemoteProtocolError", "APIConnectionError"}:
        return WriterFailure(f"The desktop connection was lost during {operation}. Retry on a fresh desktop; no typing command was replayed.", code="connection_lost", operation=operation)
    return WriterFailure(f"The desktop failed during {operation}. Retry on a fresh desktop; the approved letter is kept.", code="desktop_error", operation=operation)


def verify_pdf(data: bytes, expected: str) -> None:
    if looks_like_pdf(data):
        raise WriterFailure("Writer returned an invalid or oversized PDF. Retry the export.")
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        if not 1 <= len(reader.pages) <= 8:
            raise ValueError("Unexpected page count")
        actual = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        raise WriterFailure("Could not verify the exported PDF. Retry the export.") from None
    if not pdf_words_match(expected, actual):
        raise WriterFailure("PDF text differs from the approved letter. The PDF was not saved; retry the export.")


class OfflineWriter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.sandbox = None
        self.viewer = None
        self._view_context = None
        self._create_attempted = False
        self.operation = "opening"

    def open(self):
        try:
            from e2b_desktop import Sandbox
            from .live_view import open_live_view
        except ImportError:
            raise WriterFailure("Install the desktop dependencies with pip install -e '.[e2b,jobs]', then restart the API.") from None
        try:
            self._create_attempted = True
            self.sandbox = Sandbox.create(resolution=SCREEN, timeout=WRITER_LIFETIME,
                network=network_config(install=False), lifecycle={"on_timeout": "kill"},
                api_key=self.api_key, request_timeout=40)
            self._view_context = open_live_view(self.sandbox, cookie_max_age=WRITER_LIFETIME)
            self.viewer = self._view_context.__enter__()
        except Exception:
            raise WriterFailure("Could not open the E2B Writer desktop or its live view. Check the E2B key and connection, then retry.") from None

    def prepare(self, checkpoint):
        """Verify the network and open Writer before receiving any letter text."""
        from e2b import CommandExitException
        checkpoint()
        self.operation = "network check"
        output = self.sandbox.commands.run("timeout 20 python3 -c " + shlex.quote(GUEST_NETWORK_CHECK), timeout=35).stdout
        try:
            report = json.loads(output.strip().splitlines()[-1])
            problem = judge_network(report["checks"])
        except (ValueError, KeyError, IndexError, TypeError):
            raise WriterFailure("Could not verify the offline desktop network. No letter was typed.") from None
        if problem:
            raise WriterFailure("The desktop did not pass the offline network check. No letter was typed.")
        checkpoint()
        self.operation = "opening Writer"
        try:
            self.sandbox.commands.run("command -v soffice", timeout=10)
        except CommandExitException:
            raise WriterFailure("LibreOffice is missing from the desktop image. The Writer image must have it preinstalled; no network access was enabled.") from None
        self.sandbox.files.write(f"{WRITER_PROFILE}/user/registrymodifications.xcu", settings_xcu(WRITER_SETTINGS_OFF))
        handle = self.sandbox.commands.run(
            f"soffice -env:UserInstallation=file://{WRITER_PROFILE} --writer --norestore --nologo > /tmp/writer.log 2>&1",
            background=True, timeout=0)
        handle.disconnect()
        deadline = time.monotonic() + 60
        window = ""
        while time.monotonic() < deadline:
            checkpoint()
            try:
                found = self.sandbox.commands.run("xdotool search --onlyvisible --name 'LibreOffice Writer'", timeout=10)
                window = found.stdout.split()[-1] if found.stdout.split() else ""
            except CommandExitException:
                pass
            if window:
                break
            time.sleep(0.5)
        if not window.isdigit():
            raise WriterFailure("LibreOffice did not open in time. Retry the export.")
        time.sleep(2)
        checkpoint()
        self.sandbox.press("escape")
        self.sandbox.commands.run(f"xdotool windowactivate --sync {window}", timeout=10)
        width, height = self.sandbox.get_screen_size()
        self.sandbox.left_click(width // 2, height // 2)

    def _wait_file(self, path: str, checkpoint):
        from e2b import CommandExitException
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            checkpoint()
            try:
                size = int(self.sandbox.commands.run(f"stat -c %s {path}", timeout=10).stdout.strip())
                if 0 < size <= MAX_PDF_BYTES:
                    return
                if size > MAX_PDF_BYTES:
                    break
            except (CommandExitException, ValueError):
                pass
            time.sleep(0.5)
        raise WriterFailure("Writer did not save a usable file in time. Retry the export.")

    def _type(self, text: str, *, delay=TYPING_DELAY_MS):
        # E2B's default command locale can be ASCII. xdotool then exits on curly
        # quotes/dashes. Quote data as one shell argument and enforce UTF-8.
        self.sandbox.commands.run(
            f"LC_ALL=C.UTF-8 xdotool type --clearmodifiers --delay {delay} -- " + shlex.quote(text),
            timeout=15)

    def write_pdf(self, text: str, progress, checkpoint) -> bytes:
        if not text or len(text) > MAX_WRITER_CHARACTERS:
            raise WriterFailure("Live Writer supports approved letters up to 6,000 characters.")
        typed = 0
        self.operation = "typing"
        progress("typing", typed)
        for part in typing_plan(text):
            checkpoint()
            if part is None:
                self.sandbox.press("enter")
                typed += 1
            else:
                # Bounded chunks make cancellation responsive and progress measurable.
                for start in range(0, len(part), TYPING_CHUNK):
                    checkpoint()
                    chunk = part[start:start + TYPING_CHUNK]
                    self._type(chunk)
                    typed += len(chunk)
                    progress("typing", typed)
        progress("exporting", typed)
        self.operation = "saving document"
        checkpoint()
        self.sandbox.press(["ctrl", "s"])
        time.sleep(2)
        checkpoint()
        self._type(DOC_PATH, delay=10)
        self.sandbox.press("enter")
        self._wait_file(DOC_PATH, checkpoint)
        checkpoint()
        self.operation = "exporting PDF"
        self.sandbox.left_click(*EXPORT_PDF_BUTTON)
        time.sleep(2)
        checkpoint()
        self._type(PDF_PATH, delay=10)
        self.sandbox.press("enter")
        self._wait_file(PDF_PATH, checkpoint)
        time.sleep(1)
        checkpoint()
        self.operation = "downloading PDF"
        data = bytes(self.sandbox.files.read(PDF_PATH, format="bytes"))
        self.operation = "checking PDF"
        verify_pdf(data, text)
        return data

    def close(self) -> bool:
        """Always attempt destruction, even if viewer shutdown fails. Never log SDK bodies."""
        try:
            if self._view_context is not None:
                try:
                    self._view_context.__exit__(None, None, None)
                except Exception:
                    pass
        finally:
            if self.sandbox is not None:
                try:
                    self.sandbox.kill(request_timeout=10)
                    return True  # False from kill also means the sandbox is already absent.
                except Exception:
                    return False
        return not self._create_attempted  # A lost create response cannot prove no sandbox exists.
