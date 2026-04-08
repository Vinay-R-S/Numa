"""
SlackActionRouter — executes intents via Slack SDK and persists to Supabase.
Used by both the /chat endpoint and the Slack Bolt event handler.
"""
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import settings
from app.database import get_supabase
from app.models import IntentResponse

logger = logging.getLogger(__name__)


class _Params:
    """Wraps the parameters dict so all fields are accessible as attributes.
    Returns None for any key the LLM did not extract, preventing AttributeError."""
    def __init__(self, data: dict):
        self.__dict__.update(data)

    def __getattr__(self, name):
        return None


class SlackActionRouter:
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self._bot_user_id: Optional[str] = None

    @property
    def bot_user_id(self) -> str:
        if not self._bot_user_id:
            try:
                self._bot_user_id = self.client.auth_test()["user_id"]
            except SlackApiError:
                self._bot_user_id = ""
        return self._bot_user_id

    # ── Resolution helpers ─────────────────────────────────────────────────────

    def resolve_channel_id(self, channel_name: str) -> Optional[str]:
        name = channel_name.lstrip("#").lower()
        try:
            resp = self.client.conversations_list(
                types="public_channel,private_channel", limit=500, exclude_archived=True
            )
            for ch in resp["channels"]:
                if ch["name"].lower() == name:
                    return ch["id"]
        except SlackApiError as exc:
            logger.error(f"Channel resolve error: {exc}")
        return None

    def resolve_user_id(self, user_name: str) -> Optional[str]:
        target = user_name.lstrip("@").lower()
        try:
            resp = self.client.users_list(limit=500)
            for u in resp["members"]:
                if u.get("deleted"):
                    continue
                if (
                    u.get("name", "").lower() == target
                    or u.get("real_name", "").lower() == target
                    or u.get("profile", {}).get("display_name", "").lower() == target
                ):
                    return u["id"]
        except SlackApiError as exc:
            logger.error(f"User resolve error: {exc}")
        return None

    # ── Main dispatcher ────────────────────────────────────────────────────────

    def execute(self, intent_data: IntentResponse, user_id: Optional[str] = None) -> dict[str, Any]:
        intent = intent_data.intent
        params = _Params(intent_data.parameters if isinstance(intent_data.parameters, dict) else {})

        dispatch = {
            "send_message": lambda: self._send_message(params),
            "create_channel": lambda: self._create_channel(params),
            "rename_channel": lambda: self._rename_channel(params),
            "archive_channel": lambda: self._archive_channel(params),
            "invite_user": lambda: self._invite_user(params),
            "remove_user": lambda: self._remove_user(params),
            "list_channels": lambda: self._list_channels(),
            "list_users": lambda: self._list_users(),
            "upload_file": lambda: self._upload_file(params),
            "add_reaction": lambda: self._add_reaction(params),
            "remove_reaction": lambda: self._remove_reaction(params),
            "schedule_message": lambda: self._schedule_message(params),
            "get_history": lambda: self._get_history(params),
            # NUMA-specific
            "task_add": lambda: self._task_add(params, user_id),
            "task_list": lambda: self._task_list(user_id),
            "plan_today": lambda: self._plan_today(user_id),
            "score": lambda: self._score(user_id),
            "schedule_view": lambda: self._schedule_view(user_id),
            "unknown": lambda: {"ok": False, "error": "I didn't understand that.", "reflection": intent_data.reflection},
        }

        fn = dispatch.get(intent)
        if fn is None:
            return {"ok": False, "error": f"Intent '{intent}' not implemented."}
        try:
            return fn()
        except Exception as exc:
            logger.error(f"Execute error [{intent}]: {exc}")
            return {"ok": False, "error": str(exc)}

    # ── Slack actions ──────────────────────────────────────────────────────────

    def _send_message(self, params):
        if not params.text:
            return {"ok": False, "error": "Missing text."}
        target = None
        if params.channel_name:
            target = self.resolve_channel_id(params.channel_name)
            if not target:
                return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        elif params.user_name:
            target = self.resolve_user_id(params.user_name)
            if not target:
                return {"ok": False, "error": f"User @{params.user_name} not found."}
        if not target:
            return {"ok": False, "error": "No channel or user specified."}
        self.client.chat_postMessage(channel=target, text=params.text)
        return {"ok": True, "message": f"Message sent to {params.channel_name or params.user_name}"}

    def _create_channel(self, params):
        if not params.channel_name:
            return {"ok": False, "error": "Missing channel_name."}
        name = params.channel_name.lstrip("#")
        resp = self.client.conversations_create(name=name, is_private=False)
        cid = resp["channel"]["id"]
        try:
            self.client.conversations_invite(channel=cid, users=[self.bot_user_id])
        except SlackApiError:
            pass
        return {"ok": True, "message": f"Channel #{name} created.", "channel_id": cid}

    def _rename_channel(self, params):
        if not params.channel_name or not params.new_name:
            return {"ok": False, "error": "Missing channel_name or new_name."}
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
            return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        self.client.conversations_rename(channel=cid, name=params.new_name)
        return {"ok": True, "message": f"Channel renamed to #{params.new_name}"}

    def _archive_channel(self, params):
        if not params.channel_name:
            return {"ok": False, "error": "Missing channel_name."}
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
            return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        self.client.conversations_archive(channel=cid)
        return {"ok": True, "message": f"Channel #{params.channel_name} archived."}

    def _invite_user(self, params):
        if not params.channel_name or not params.user_name:
            return {"ok": False, "error": "Missing channel_name or user_name."}
        cid = self.resolve_channel_id(params.channel_name)
        uid = self.resolve_user_id(params.user_name)
        if not cid or not uid:
            return {"ok": False, "error": "Channel or user not found."}
        self.client.conversations_invite(channel=cid, users=[uid])
        return {"ok": True, "message": f"@{params.user_name} invited to #{params.channel_name}"}

    def _remove_user(self, params):
        if not params.channel_name or not params.user_name:
            return {"ok": False, "error": "Missing params."}
        cid = self.resolve_channel_id(params.channel_name)
        uid = self.resolve_user_id(params.user_name)
        if not cid or not uid:
            return {"ok": False, "error": "Channel or user not found."}
        self.client.conversations_kick(channel=cid, user=uid)
        return {"ok": True, "message": f"@{params.user_name} removed from #{params.channel_name}"}

    def _list_channels(self):
        resp = self.client.conversations_list(types="public_channel", limit=100, exclude_archived=True)
        names = [f"#{ch['name']}" for ch in resp["channels"]]
        return {"ok": True, "message": f"Channels: {', '.join(names)}", "channels": names}

    def _list_users(self):
        resp = self.client.users_list(limit=200)
        names = [u.get("real_name") or u["name"] for u in resp["members"] if not u.get("deleted") and not u.get("is_bot")]
        return {"ok": True, "message": f"Users: {', '.join(names[:20])}", "users": names}

    def _upload_file(self, params):
        if not params.file_content:
            return {"ok": False, "error": "Missing file_content."}
        channel = self.resolve_channel_id(params.channel_name) if params.channel_name else None
        self.client.files_upload_v2(
            content=params.file_content,
            filename=params.filename or "snippet.txt",
            channels=[channel] if channel else [],
        )
        return {"ok": True, "message": "File uploaded."}

    def _add_reaction(self, params):
        if not params.reaction_name or not params.thread_ts or not params.channel_name:
            return {"ok": False, "error": "Missing reaction_name, thread_ts, or channel_name."}
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
            return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        self.client.reactions_add(channel=cid, name=params.reaction_name, timestamp=params.thread_ts)
        return {"ok": True, "message": f":{params.reaction_name}: added"}

    def _remove_reaction(self, params):
        if not params.reaction_name or not params.thread_ts or not params.channel_name:
            return {"ok": False, "error": "Missing params."}
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
            return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        self.client.reactions_remove(channel=cid, name=params.reaction_name, timestamp=params.thread_ts)
        return {"ok": True, "message": f":{params.reaction_name}: removed"}

    def _schedule_message(self, params):
        if not params.text or not params.channel_name or not params.post_at:
            return {"ok": False, "error": "Missing text, channel_name, or post_at."}
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
            return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        import time, dateparser
        parsed_dt = dateparser.parse(params.post_at)
        if not parsed_dt:
            return {"ok": False, "error": f"Could not parse time: {params.post_at}"}
        self.client.chat_scheduleMessage(
            channel=cid, text=params.text, post_at=int(parsed_dt.timestamp())
        )
        return {"ok": True, "message": f"Message scheduled for {params.post_at}"}

    def _get_history(self, params):
        if not params.channel_name:
            return {"ok": False, "error": "Missing channel_name."}
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
            return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        resp = self.client.conversations_history(channel=cid, limit=params.count or 10)
        messages = [{"ts": m["ts"], "text": m.get("text", "")} for m in resp["messages"]]
        return {"ok": True, "message": f"Last {len(messages)} messages", "messages": messages}

    # ── NUMA-specific actions ──────────────────────────────────────────────────

    def _task_add(self, params, user_id: Optional[str]):
        if not user_id:
            return {"ok": False, "error": "Not authenticated."}
        title = params.task_title or params.text
        if not title:
            return {"ok": False, "error": "Missing task title."}
        db = get_supabase()
        resp = db.table("tasks").insert({
            "user_id": user_id,
            "title": title,
            "status": "todo",
            "priority": "medium",
            "source": "slack",
        }).execute()
        task = resp.data[0]
        # Update daily analytics
        self._bump_analytics(user_id, "tasks_created")
        return {"ok": True, "message": f"Task added: *{title}*", "task_id": task["id"]}

    def _task_list(self, user_id: Optional[str]):
        if not user_id:
            return {"ok": False, "error": "Not authenticated."}
        db = get_supabase()
        resp = db.table("tasks").select("title,status,priority").eq("user_id", user_id).eq("status", "todo").order("created_at", desc=True).limit(10).execute()
        tasks = resp.data or []
        if not tasks:
            return {"ok": True, "message": "No open tasks. Great work!"}
        lines = "\n".join(f"• {t['title']} [{t['priority']}]" for t in tasks)
        return {"ok": True, "message": f"Your open tasks:\n{lines}"}

    def _plan_today(self, user_id: Optional[str]):
        if not user_id:
            return {"ok": False, "error": "Not authenticated."}
        today = date.today().isoformat()
        db = get_supabase()
        resp = db.table("plans").select("*").eq("user_id", user_id).eq("plan_date", today).limit(1).execute()
        if resp.data:
            plan = resp.data[0]
            blocks = plan.get("blocks", [])
            lines = "\n".join(f"• {b['label']} {b['start_time']}–{b['end_time']} [{b['tag']}]" for b in blocks)
            return {"ok": True, "message": f"Today's plan:\n{lines}" if lines else "Plan exists but no blocks yet."}
        return {"ok": True, "message": "No plan yet. Visit your NUMA dashboard to generate one."}

    def _score(self, user_id: Optional[str]):
        if not user_id:
            return {"ok": False, "error": "Not authenticated."}
        today = date.today().isoformat()
        db = get_supabase()
        resp = db.table("analytics").select("productivity_score,tasks_completed").eq("user_id", user_id).eq("period_date", today).limit(1).execute()
        if resp.data:
            d = resp.data[0]
            return {"ok": True, "message": f"Today's score: *{d.get('productivity_score', '—')}%*\nTasks completed: {d.get('tasks_completed', 0)}"}
        return {"ok": True, "message": "No score yet for today. Complete tasks to start building your score."}

    def _schedule_view(self, user_id: Optional[str]):
        return self._plan_today(user_id)

    def _bump_analytics(self, user_id: str, field: str):
        """Increment an analytics counter for today."""
        try:
            today = date.today().isoformat()
            db = get_supabase()
            resp = db.table("analytics").select("id," + field).eq("user_id", user_id).eq("period_date", today).limit(1).execute()
            if resp.data:
                row = resp.data[0]
                db.table("analytics").update({field: (row.get(field) or 0) + 1}).eq("id", row["id"]).execute()
            else:
                db.table("analytics").insert({"user_id": user_id, "period_date": today, field: 1}).execute()
        except Exception as exc:
            logger.warning(f"Analytics bump failed: {exc}")
