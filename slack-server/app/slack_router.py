
import logging
from typing import Optional, Dict, List, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import settings
from app.models import IntentResponse, IntentParameters

logger = logging.getLogger(__name__)

class SlackRouter:
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)
        self.bot_user_id = self._get_bot_user_id()

    def _get_bot_user_id(self) -> str:
        try:
            auth = self.client.auth_test()
            return auth["user_id"]
        except SlackApiError:
            return ""

    # ----------------------------------------------------------------
    # Resolution Helpers (Deterministic)
    # ----------------------------------------------------------------

    def resolve_channel_id(self, channel_name: str) -> Optional[str]:
        """
        Resolves a channel name to an ID by listing all public/private channels.
        Returns None if not found.
        """
        if not channel_name:
            return None
        
        # Clean input
        target_name = channel_name.lstrip("#").lower()
        
        try:
            # We list up to 500 channels to be safe. 
            # In huge workspaces, this might need cursor pagination, but for now this is robust enough.
            response = self.client.conversations_list(
                types="public_channel,private_channel", 
                limit=500,
                exclude_archived=True
            )
            for channel in response["channels"]:
                if channel["name"].lower() == target_name:
                    return channel["id"]
            return None
        except SlackApiError as e:
            logger.error(f"Error resolving channel {channel_name}: {e}")
            return None

    def resolve_user_id(self, user_name: str) -> Optional[str]:
        """
        Resolves a user name (display name or real name) to an ID.
        """
        if not user_name:
            return None

        target_name = user_name.lstrip("@").lower()
        
        try:
            response = self.client.users_list(limit=500)
            for user in response["members"]:
                if user.get("deleted"):
                    continue
                
                # Check names
                is_match = (
                    user.get("name", "").lower() == target_name or
                    user.get("real_name", "").lower() == target_name or
                    user.get("profile", {}).get("display_name", "").lower() == target_name
                )
                if is_match:
                    return user["id"]
            return None
        except SlackApiError as e:
            logger.error(f"Error resolving user {user_name}: {e}")
            return None

    # ----------------------------------------------------------------
    # Action Executors
    # ----------------------------------------------------------------

    def execute(self, intent_data: IntentResponse) -> Dict[str, Any]:
        """
        Main router method. Switches on intent and executes logic.
        """
        intent = intent_data.intent
        params = intent_data.parameters

        try:
            if intent == "send_message":
                return self._send_message(params)
            elif intent == "create_channel":
                return self._create_channel(params)
            elif intent == "rename_channel":
                return self._rename_channel(params)
            elif intent == "archive_channel":
                return self._archive_channel(params)
            elif intent == "invite_user":
                return self._invite_user(params)
            elif intent == "remove_user":
                return self._remove_user(params)
            elif intent == "list_channels":
                return self._list_channels(params)
            elif intent == "list_users":
                return self._list_users(params)
            elif intent == "upload_file":
                return self._upload_file(params)
            elif intent == "add_reaction":
                return self._add_reaction(params)
            elif intent == "remove_reaction":
                return self._remove_reaction(params)
            elif intent == "schedule_message":
                return self._schedule_message(params)
            elif intent == "unknown":
                return {"ok": False, "error": "Could not understand request.", "reflection": intent_data.reflection}
            else:
                return {"ok": False, "error": f"Intent '{intent}' not implemented yet."}
        
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            return {"ok": False, "error": str(e)}

    # --- Implementation Details ---

    def _send_message(self, params: IntentParameters):
        if not params.text:
            return {"ok": False, "error": "Missing 'text' parameter."}
        
        target_id = None
        target_name = ""

        # Priority 1: Channel
        if params.channel_name:
            target_id = self.resolve_channel_id(params.channel_name)
            target_name = params.channel_name
            if not target_id:
                 return {"ok": False, "error": f"Channel '#{params.channel_name}' not found."}

        # Priority 2: User (Direct Message)
        elif params.user_name:
            target_id = self.resolve_user_id(params.user_name)
            target_name = params.user_name
            if not target_id:
                 return {"ok": False, "error": f"User '@{params.user_name}' not found."}
        
        if not target_id:
             return {"ok": False, "error": "No channel or user specified."}

        # Execute
        self.client.chat_postMessage(channel=target_id, text=params.text)
        return {"ok": True, "message": f"Message sent to {target_name}"}

    def _create_channel(self, params: IntentParameters):
        if not params.channel_name:
             return {"ok": False, "error": "Missing 'channel_name'."}
        
        name = params.channel_name.lstrip("#")
        resp = self.client.conversations_create(name=name, is_private=False)
        channel_id = resp["channel"]["id"]
        
        # Invite bot
        try:
            self.client.conversations_invite(channel=channel_id, users=[self.bot_user_id])
        except SlackApiError:
            pass # Already in channel

        return {"ok": True, "message": f"Channel #{name} created.", "channel_id": channel_id}

    def _rename_channel(self, params: IntentParameters):
        if not params.channel_name or not params.new_name:
             return {"ok": False, "error": "Missing 'channel_name' or 'new_name'."}

        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        
        self.client.conversations_rename(channel=cid, name=params.new_name)
        return {"ok": True, "message": f"Channel renamed to #{params.new_name}"}

    def _archive_channel(self, params: IntentParameters):
        if not params.channel_name:
             return {"ok": False, "error": "Missing 'channel_name'."}

        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        
        self.client.conversations_archive(channel=cid)
        return {"ok": True, "message": f"Channel #{params.channel_name} archived."}

    def _invite_user(self, params: IntentParameters):
        if not params.channel_name or not params.user_name:
             return {"ok": False, "error": "Missing 'channel_name' or 'user_name'."}
        
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        
        uid = self.resolve_user_id(params.user_name)
        if not uid:
             return {"ok": False, "error": f"User @{params.user_name} not found."}
        
        self.client.conversations_invite(channel=cid, users=[uid])
        return {"ok": True, "message": f"User @{params.user_name} invited to #{params.channel_name}"}

    def _remove_user(self, params: IntentParameters):
        if not params.channel_name or not params.user_name:
             return {"ok": False, "error": "Missing 'channel_name' or 'user_name'."}

        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        
        uid = self.resolve_user_id(params.user_name)
        if not uid:
             return {"ok": False, "error": f"User @{params.user_name} not found."}
        
        self.client.conversations_kick(channel=cid, user=uid)
        return {"ok": True, "message": f"User @{params.user_name} removed from #{params.channel_name}"}

    def _list_channels(self, params: IntentParameters):
        resp = self.client.conversations_list(types="public_channel,private_channel", limit=100)
        channels = [f"#{c['name']}" for c in resp['channels']]
        return {"ok": True, "channels": channels}

    def _list_users(self, params: IntentParameters):
        resp = self.client.users_list(limit=50)
        users = [f"@{u['name']}" for u in resp['members'] if not u.get('deleted') and not u.get('is_bot')]
        return {"ok": True, "users": users}

    def _upload_file(self, params: IntentParameters):
        if not params.channel_name or not params.file_content or not params.filename:
            return {"ok": False, "error": "Missing channel, content, or filename."}
        
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        
        resp = self.client.files_upload_v2(
            channel=cid,
            content=params.file_content,
            filename=params.filename
        )
        return {"ok": True, "message": "File uploaded."}

    def _add_reaction(self, params: IntentParameters):
        if not params.channel_name or not params.reaction_name:
             return {"ok": False, "error": "Missing 'channel_name' or 'reaction_name'."}

        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        
        # Clean reaction name
        name = params.reaction_name.strip(":").lower()
        # Common mappings
        mappings = {
            "thumbs_up": "+1",
            "thumbsup": "+1",
            "check": "white_check_mark",
            "tick": "white_check_mark"
        }
        name = mappings.get(name, name)
        
        ts = params.thread_ts
        if not ts:
            try:
                # Fallback: get latest message
                history = self.client.conversations_history(channel=cid, limit=1)
                if history['messages']:
                    ts = history['messages'][0]['ts']
                else:
                    return {"ok": False, "error": "No messages found in channel to react to."}
            except SlackApiError as e:
                if e.response.get("error") == "missing_scope":
                     needed = e.response.get("needed", "channels:history")
                     return {"ok": False, "error": f"Missing Slack Scope. Please add '{needed}' to your Bot Token Scopes and reinstall the app."}
                return {"ok": False, "error": f"Failed to fetch history: {e}"}

        try:
            self.client.reactions_add(channel=cid, name=name, timestamp=ts)
            return {"ok": True, "message": f"Added :{name}: to message."}
        except SlackApiError as e:
            return {"ok": False, "error": str(e)}

    def _remove_reaction(self, params: IntentParameters):
        if not params.channel_name or not params.reaction_name:
             return {"ok": False, "error": "Missing 'channel_name' or 'reaction_name'."}

        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}
        
        # Clean reaction name
        name = params.reaction_name.strip(":").lower()
        # Common mappings
        mappings = {
            "thumbs_up": "+1",
            "thumbsup": "+1",
            "check": "white_check_mark",
            "tick": "white_check_mark"
        }
        name = mappings.get(name, name)
        
        ts = params.thread_ts
        if not ts:
            try:
                history = self.client.conversations_history(channel=cid, limit=1)
                if history['messages']:
                    ts = history['messages'][0]['ts']
                else:
                    return {"ok": False, "error": "No messages found in channel."}
            except SlackApiError as e:
                if e.response.get("error") == "missing_scope":
                     needed = e.response.get("needed", "channels:history")
                     return {"ok": False, "error": f"Missing Slack Scope. Please add '{needed}' to your Bot Token Scopes and reinstall the app."}
                return {"ok": False, "error": "Failed to fetch history."}

        try:
            self.client.reactions_remove(channel=cid, name=name, timestamp=ts)
            return {"ok": True, "message": f"Removed :{name}: from message."}
        except SlackApiError as e:
            return {"ok": False, "error": str(e)}

    def _schedule_message(self, params: IntentParameters):
        if not params.channel_name or not params.text or not params.post_at:
             return {"ok": False, "error": "Missing channel, text, or post_at time."}
             
        cid = self.resolve_channel_id(params.channel_name)
        if not cid:
             return {"ok": False, "error": f"Channel #{params.channel_name} not found."}

        try:
            post_at_ts = int(params.post_at)
            self.client.chat_scheduleMessage(channel=cid, text=params.text, post_at=post_at_ts)
            return {"ok": True, "message": f"Message scheduled."}
        except ValueError:
             return {"ok": False, "error": "post_at must be a Unix timestamp."}
        except SlackApiError as e:
            return {"ok": False, "error": str(e)}

# Singleton instance
router = SlackRouter()
