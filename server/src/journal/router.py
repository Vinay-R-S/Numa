"""
Journal Router - CRUD endpoints + AI summary generation.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.dependencies import get_current_user
from ..db import _get_conn
from .schemas import (
    JournalEntryCreate,
    JournalEntryOut,
    JournalEntryUpdate,
    JournalListResponse,
    JournalSummaryRequest,
    JournalSummaryResponse,
)

router = APIRouter(prefix="/api/journal", tags=["journal"])


def _row_to_entry(row, description) -> JournalEntryOut:
    d = {col.name: val for col, val in zip(description, row)}
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

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM public.journal_entries WHERE user_id = %s",
            (user_id,),
        )
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT id, user_id, title, content, mood, entry_date, tags, ai_summary,
                   created_at, updated_at
            FROM public.journal_entries
            WHERE user_id = %s
            ORDER BY entry_date DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        rows = cur.fetchall()
        entries = [_row_to_entry(r, cur.description) for r in rows]
        cur.close()
        return JournalListResponse(entries=entries, total=total)
    finally:
        conn.close()


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

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.journal_entries
                (user_id, title, content, mood, entry_date, tags)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, entry_date) DO UPDATE SET
                title      = EXCLUDED.title,
                content    = EXCLUDED.content,
                mood       = EXCLUDED.mood,
                tags       = EXCLUDED.tags,
                updated_at = NOW()
            RETURNING id, user_id, title, content, mood, entry_date, tags, ai_summary,
                      created_at, updated_at
            """,
            (
                user_id,
                generated["title"],
                generated["content"],
                generated.get("mood"),
                entry_date,
                generated.get("tags", []),
            ),
        )
        row = cur.fetchone()
        entry = _row_to_entry(row, cur.description)
        conn.commit()
        cur.close()
        return entry
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"Failed to save auto-generated entry: {exc}")
    finally:
        conn.close()


@router.get("/{entry_date}", response_model=JournalEntryOut)
def get_entry(entry_date: date, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, user_id, title, content, mood, entry_date, tags, ai_summary,
                   created_at, updated_at
            FROM public.journal_entries
            WHERE user_id = %s AND entry_date = %s
            """,
            (user_id, entry_date),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            raise HTTPException(404, f"No journal entry for {entry_date}")
        return _row_to_entry(row, cur.description)
    finally:
        conn.close()


@router.post("", response_model=JournalEntryOut, status_code=201)
def create_entry(body: JournalEntryCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    entry_date = body.entry_date or date.today()

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.journal_entries
                (user_id, title, content, mood, entry_date, tags)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, entry_date) DO UPDATE SET
                title      = EXCLUDED.title,
                content    = EXCLUDED.content,
                mood       = EXCLUDED.mood,
                tags       = EXCLUDED.tags,
                updated_at = NOW()
            RETURNING id, user_id, title, content, mood, entry_date, tags, ai_summary,
                      created_at, updated_at
            """,
            (user_id, body.title, body.content, body.mood, entry_date, body.tags),
        )
        row = cur.fetchone()
        entry = _row_to_entry(row, cur.description)
        conn.commit()
        cur.close()
        return entry
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"Failed to save journal entry: {exc}")
    finally:
        conn.close()


@router.put("/{entry_date}", response_model=JournalEntryOut)
def update_entry(
    entry_date: date,
    body: JournalEntryUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    sets = []
    params = []
    if body.title is not None:
        sets.append("title = %s")
        params.append(body.title)
    if body.content is not None:
        sets.append("content = %s")
        params.append(body.content)
    if body.mood is not None:
        sets.append("mood = %s")
        params.append(body.mood)
    if body.tags is not None:
        sets.append("tags = %s")
        params.append(body.tags)

    if not sets:
        raise HTTPException(400, "No fields to update")

    sets.append("updated_at = NOW()")
    params.extend([user_id, entry_date])

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE public.journal_entries
            SET {', '.join(sets)}
            WHERE user_id = %s AND entry_date = %s
            RETURNING id, user_id, title, content, mood, entry_date, tags, ai_summary,
                      created_at, updated_at
            """,
            params,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"No journal entry for {entry_date}")
        entry = _row_to_entry(row, cur.description)
        conn.commit()
        cur.close()
        return entry
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"Failed to update journal entry: {exc}")
    finally:
        conn.close()


@router.delete("/{entry_date}", status_code=204)
def delete_entry(entry_date: date, current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(401, "Missing user session")

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM public.journal_entries WHERE user_id = %s AND entry_date = %s",
            (user_id, entry_date),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, f"No journal entry for {entry_date}")
        conn.commit()
        cur.close()
    except HTTPException:
        raise
    finally:
        conn.close()


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

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE public.journal_entries
            SET ai_summary = %s, updated_at = NOW()
            WHERE user_id = %s AND entry_date = %s
            """,
            (summary, user_id, target_date),
        )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

    return JournalSummaryResponse(summary=summary, entry_date=target_date)
