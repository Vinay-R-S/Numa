"""
One-time cleanup script to remove duplicate calendar event tasks.

This script identifies and removes duplicate tasks created from the same calendar event
appearing in multiple calendars. It keeps the first occurrence and deletes duplicates.

Run this once after deploying the iCalUID fix.
"""

from ..db import _get_conn


def cleanup_duplicate_calendar_tasks():
    """Remove duplicate calendar event tasks, keeping only one per unique event."""
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # Find duplicate tasks with similar titles, due_dates, and source
        # that were created from calendar events (have external_ref starting with 'gcal:')
        cur.execute(
            """
            WITH duplicates AS (
                SELECT
                    id,
                    user_id,
                    title,
                    due_date,
                    external_ref,
                    created_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, title, due_date
                        ORDER BY created_at ASC
                    ) as rn
                FROM public.tasks
                WHERE
                    source_name = 'Google Calendar'
                    AND external_ref LIKE 'gcal:%'
                    AND external_ref NOT LIKE 'gcal:ical:%'
            )
            SELECT id, user_id, title, external_ref
            FROM duplicates
            WHERE rn > 1
            """
        )

        duplicates = cur.fetchall()

        if not duplicates:
            print("No duplicate calendar tasks found.")
            conn.close()
            return

        print(f"Found {len(duplicates)} duplicate calendar tasks.")

        # Delete duplicates
        for task_id, user_id, title, external_ref in duplicates:
            print(f"Deleting duplicate: {title} (id={task_id}, ref={external_ref})")
            cur.execute(
                "DELETE FROM public.tasks WHERE id = %s AND user_id = %s",
                (task_id, user_id),
            )

        conn.commit()
        print(f"Successfully removed {len(duplicates)} duplicate tasks.")
        cur.close()
    except Exception as exc:
        print(f"Error during cleanup: {exc}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    print("Starting duplicate calendar task cleanup...")
    cleanup_duplicate_calendar_tasks()
    print("Cleanup complete!")
