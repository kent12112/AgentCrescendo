"""Local caches for job search (JOB-F06): company lists and each board's postings.

Why: Common Crawl changes monthly and its index server is often overloaded, and a
search over ~1,000+ boards should not refetch them all every time. Two caches,
both plain JSON under an ignored directory (default ``.cache/jobs``):

- ``companies-<source>.json``: discovered board slugs, reused for ~30 days, and
  reused past that when a refresh fails (stale beats nothing).
- ``boards/<source>-<slug>.json``: one board's normalized postings, reused for
  ~24 hours. Only "board does not exist" (HTTP 404) is cached as a failure;
  timeouts and server errors are retried next run.

Files hold only our own normalized output of public job data, never resume text.
A missing, corrupt, or unexpected file is a cache miss, never an error.
"""
from dataclasses import asdict, fields
import json
import os
from pathlib import Path
import time

from .job_sources import BoardResult, CompanyBoard, Posting, fetch_boards

DEFAULT_ROOT = Path(".cache/jobs")
FORMAT = 1
_POSTING_FIELDS = {f.name for f in fields(Posting)}
_TUPLE_FIELDS = {"locations", "countries"}


def _write_json(path: Path, data) -> None:
    """Write via a temporary file so a crash never leaves half a cache file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False))
    os.replace(temporary, path)


def _read_json(path: Path):
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("format") == FORMAT else None


def _posting(data) -> Posting:
    """Rebuild a Posting from its cached dict. Raises on any unexpected shape."""
    if not isinstance(data, dict) or set(data) - _POSTING_FIELDS:
        raise ValueError("unexpected posting fields")
    values = {key: tuple(value) if key in _TUPLE_FIELDS else value for key, value in data.items()}
    return Posting(**values)


class JobCache:
    def __init__(self, root=DEFAULT_ROOT, *, now=time.time):
        self.root = Path(root)
        self.now = now

    # Company lists -------------------------------------------------------
    def _companies_path(self, source: str) -> Path:
        return self.root / f"companies-{source}.json"

    def load_companies(self, source: str, max_age_days: float | None = 30):
        """(boards, saved_at, details) if a list exists and is fresh enough, else None.

        ``max_age_days=None`` accepts any age (used when a refresh failed).
        """
        data = _read_json(self._companies_path(source))
        if not data or not isinstance(data.get("saved_at"), (int, float)):
            return None
        if max_age_days is not None and self.now() - data["saved_at"] > max_age_days * 86400:
            return None
        boards = []
        for slug in data.get("slugs") or []:
            try:
                boards.append(CompanyBoard.parse(f"{source}:{slug}"))
            except (ValueError, TypeError):
                continue
        return (boards, data["saved_at"], data.get("details") or {}) if boards else None

    def save_companies(self, source: str, boards, details=None, *, saved_at: float | None = None) -> None:
        _write_json(self._companies_path(source), {
            "format": FORMAT, "saved_at": self.now() if saved_at is None else saved_at, "source": source,
            "slugs": sorted({b.slug for b in boards if b.source == source}), "details": details or {}})

    # Board postings ------------------------------------------------------
    def _board_path(self, board: CompanyBoard) -> Path:
        # Slugs passed CompanyBoard.parse: letters, digits, '_', '.', '-', no '/', not starting with '.'.
        return self.root / "boards" / f"{board.source}-{board.slug.lower()}.json"

    def load_board(self, board: CompanyBoard, max_age_hours: float) -> BoardResult | None:
        data = _read_json(self._board_path(board))
        if (not data or data.get("board") != f"{board.source}:{board.slug.lower()}"
                or not isinstance(data.get("saved_at"), (int, float))
                or self.now() - data["saved_at"] > max_age_hours * 3600):
            return None
        try:
            postings = [_posting(item) for item in data.get("postings") or []]
        except (TypeError, ValueError):
            return None
        error = data.get("error") if isinstance(data.get("error"), str) else None
        return BoardResult(board, postings=postings, skipped=int(data.get("skipped") or 0), error=error)

    def save_board(self, result: BoardResult) -> bool:
        """Cache a successful fetch or a missing board (404). Returns whether it was cached."""
        if result.error and "HTTP 404" not in result.error:
            return False
        board = result.board
        _write_json(self._board_path(board), {
            "format": FORMAT, "saved_at": self.now(), "board": f"{board.source}:{board.slug.lower()}",
            "error": result.error, "skipped": result.skipped,
            "postings": [asdict(p) for p in result.postings]})
        return True


def fetch_boards_cached(boards, cache: JobCache | None, client=None, *, max_age_hours: float = 24,
                        workers: int = 8) -> tuple[list[BoardResult], int]:
    """Like fetch_boards, but reuses cached boards. Returns (results in input order, cache hits)."""
    boards = list(boards)
    if cache is None or max_age_hours <= 0:
        return fetch_boards(boards, client, workers=workers), 0
    cached = {i: cache.load_board(board, max_age_hours) for i, board in enumerate(boards)}
    missing = [i for i, result in cached.items() if result is None]
    fetched = fetch_boards([boards[i] for i in missing], client, workers=workers) if missing else []
    for i, result in zip(missing, fetched):
        cache.save_board(result)
        cached[i] = result
    return [cached[i] for i in range(len(boards))], len(boards) - len(missing)


def refresh_company_list(client, cache: JobCache, source: str = "ashby", *, crawls: int = 6,
                         budget_seconds: float | None = 20 * 60, full: bool = False, progress=None,
                         crawl=None, retry_failed_after_days: float | None = None) -> dict:
    """Incrementally refresh the saved Common Crawl company list.

    Crawls already read are skipped; new companies are merged into the saved list,
    so a partial or failed refresh never shrinks it. A crawl that failed is retried
    on a later refresh; with ``retry_failed_after_days`` set, not until that long
    after its last failure (live, the same 4 crawls returned HTTP 504 all day, costing
    ~10 minutes per attempt). ``full`` ignores the saved list. Returns a summary dict
    with ``boards`` (the list now in use), ``added``, ``read`` (crawls read now),
    ``deferred`` (failed crawls not retried yet), ``errors``.
    """
    from .common_crawl import INDEX_ID

    if crawl is None:
        from .common_crawl import crawl_boards as crawl
    saved = None if full else cache.load_companies(source, max_age_days=None)
    old_boards, read_before = (saved[0], list(saved[2].get("indexes_read") or [])) if saved else ([], [])
    attempts = dict((saved[2].get("failed_attempts") or {}) if saved else {})
    now = cache.now()
    deferred = sorted(index for index, when in attempts.items() if retry_failed_after_days is not None
                      and isinstance(when, (int, float)) and now - when < retry_failed_after_days * 86400)
    result = crawl(client, source, crawls=crawls, skip=read_before + deferred, budget_seconds=budget_seconds,
                   progress=progress)
    # crawl_boards reports one "<index>: <reason>" error per crawl that failed.
    failed_now = [error.split(":", 1)[0] for error in result.errors if INDEX_ID.match(error.split(":", 1)[0])]
    for index in result.indexes_read:
        attempts.pop(index, None)
    for index in failed_now:
        attempts[index] = now
    merged = sorted(set(old_boards) | set(result.boards), key=lambda b: b.slug)
    if result.indexes_read or failed_now:
        indexes = sorted(set(read_before) | set(result.indexes_read), reverse=True)
        # Recording only failures keeps the list's saved date (its age means "last new crawl read").
        cache.save_companies(source, merged, {"indexes_read": indexes, "failed_attempts": attempts,
                                              "last_errors": result.errors},
                             saved_at=None if result.indexes_read or not saved else saved[1])
    return {"boards": merged, "previous": len(old_boards), "added": len(merged) - len(old_boards),
            "read": list(result.indexes_read), "read_before": read_before, "deferred": deferred,
            "errors": list(result.errors)}
