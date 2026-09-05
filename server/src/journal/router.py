"""
Journal Router - CRUD endpoints + AI summary generation.
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user
from .repository import journal_repository
from .schemas import (
    JournalEntryCreate,
    JournalEntryOut,
    JournalEntryUpdate,
    JournalListResponse,
    JournalSummaryRequest,
    JournalSummaryResponse,
)

# Mounted at both /journal and /api/journal (main.py alias).
log = logging.getLogger(__name__)

router = APIRouter(prefix="/journal", tags=["journal"])


def _row_to_entry(d: dict) -> JournalEntryOut:
    return JournalEntryOut(
        id=str(d["id"]),
        user_id=str(d["user_id"]),
        title=d.get("title", ""),
        content=d.get("content", ""),
        mood=d.get("mood"),
        entry_date=d["entry_date"],
        tags=d.get("tags") or [],
        ai_summary=d.get("ai_summary"),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


@router.get("", response_model=JournalListResponse)
def list_entries(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    total = journal_repository.count(user_id)
    rows = journal_repository.list(user_id, limit, offset)
    entries = [_row_to_entry(r) for r in rows]
    return JournalListResponse(entries=entries, total=total)


@router.post("/auto-generate", response_model=JournalEntryOut)
def auto_generate_journal(current_user: dict = Depends(get_current_user)):
    """Collect data from all connected apps and auto-generate today's journal entry."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    from .service import auto_generate_journal_entry

    try:
        generated = auto_generate_journal_entry(user_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Auto-generation failed: {exc}")

    entry_date = generated.get("entry_date", date.today())

    try:
        entry = journal_repository.upsert(
            user_id=user_id,
            title=generated["title"],
            content=generated["content"],
            mood=generated.get("mood"),
            entry_date=entry_date,
            tags=generated.get("tags", []),
        )
    except Exception as exc:
        raise HTTPException(500, f"Failed to save auto-generated entry: {exc}")
    return _row_to_entry(entry)


@router.get("/{entry_date}", response_model=JournalEntryOut)
def get_entry(entry_date: date, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    row = journal_repository.get(user_id, entry_date)
    if not row:
        raise HTTPException(404, f"No journal entry for {entry_date}")
    return _row_to_entry(row)


@router.post("", response_model=JournalEntryOut, status_code=201)
def create_entry(body: JournalEntryCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    entry_date = body.entry_date or date.today()

    try:
        entry = journal_repository.upsert(
            user_id=user_id,
            title=body.title,
            content=body.content,
            mood=body.mood,
            entry_date=entry_date,
            tags=body.tags,
        )
    except Exception as exc:
        raise HTTPException(500, f"Failed to save journal entry: {exc}")
    return _row_to_entry(entry)


@router.put("/{entry_date}", response_model=JournalEntryOut)
def update_entry(
    entry_date: date,
    body: JournalEntryUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    fields: dict = {}
    if body.title is not None:
        fields["title"] = body.title
    if body.content is not None:
        fields["content"] = body.content
    if body.mood is not None:
        fields["mood"] = body.mood
    if body.tags is not None:
        fields["tags"] = body.tags

    if not fields:
        raise HTTPException(400, "No fields to update")

    try:
        entry = journal_repository.update_fields(user_id, entry_date, fields)
    except Exception as exc:
        raise HTTPException(500, f"Failed to update journal entry: {exc}")
    if not entry:
        raise HTTPException(404, f"No journal entry for {entry_date}")
    return _row_to_entry(entry)


@router.delete("/{entry_date}", status_code=204)
def delete_entry(entry_date: date, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    deleted = journal_repository.delete(user_id, entry_date)
    if deleted == 0:
        raise HTTPException(404, f"No journal entry for {entry_date}")


@router.post("/summarize", response_model=JournalSummaryResponse)
def summarize_day(
    body: JournalSummaryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate an AI summary of the user's day using journal + other sub-agent data."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    target_date = body.entry_date or date.today()

    from .service import generate_daily_summary
    summary = generate_daily_summary(user_id, target_date)

    try:
        journal_repository.set_summary(user_id, target_date, summary)
    except Exception:
        # The summary still goes back in the response, so the caller sees a
        # success it will not find again on the next load. Never silent
        # (NUMA-141 P6, PLAN 7).
        log.warning("Failed to persist the daily summary for %s", target_date, exc_info=True)

    return JournalSummaryResponse(summary=summary, entry_date=target_date)
