"""Local tracker serialization. Application writes never contact a job board."""
from .application_models import JobApplication
from .job_search import _iso


def application_info(row: JobApplication, posting=None) -> dict:
    return {"source": row.source, "posting_id": row.posting_id, "posting": row.posting,
            "status": row.status, "applied_on": row.applied_on.isoformat() if row.applied_on else None,
            "follow_up_on": row.follow_up_on.isoformat() if row.follow_up_on else None,
            "notes": row.notes, "version": row.version,
            "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at),
            "posting_state": "expired" if posting is None else "closed" if posting.closed_at else "open"}
