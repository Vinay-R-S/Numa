
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

# Define allowed intents
IntentType = Literal[
    "send_message",
    "reply_thread",
    "edit_message",
    "delete_message",
    "create_channel",
    "rename_channel",
    "archive_channel",
    "invite_user",
    "remove_user",
    "upload_file",
    "delete_file",
    "list_channels",
    "list_users",
    "get_history",
    "add_reaction",
    "remove_reaction",
    "schedule_message",
    "unknown"
]

class IntentParameters(BaseModel):
    channel_name: Optional[str] = Field(None, description="Name of the channel (without #)")
    user_name: Optional[str] = Field(None, description="Name of the user")
    text: Optional[str] = Field(None, description="Message text content")
    new_name: Optional[str] = Field(None, description="New name for channel rename")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp for replies, or message timestamp for reactions")
    file_content: Optional[str] = Field(None, description="Content of file to upload")
    filename: Optional[str] = Field(None, description="Name of file to upload")
    count: Optional[int] = Field(10, description="Number of items to list/fetch")
    reaction_name: Optional[str] = Field(None, description="Name of the emoji reaction (without :)")
    post_at: Optional[str] = Field(None, description="Time to schedule message")

class IntentResponse(BaseModel):
    intent: IntentType = Field(..., description="The classified intent of the user action")
    parameters: IntentParameters = Field(default_factory=IntentParameters, description="Extracted parameters for the action")
    reflection: str = Field(..., description="Brief thought process about why this intent was chosen")
