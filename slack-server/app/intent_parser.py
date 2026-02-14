
import json
import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.config import settings
from app.models import IntentResponse

logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    groq_api_key=settings.GROQ_API_KEY
)

# Define the parser
parser = PydanticOutputParser(pydantic_object=IntentResponse)

# System Prompt
SYSTEM_PROMPT = """You are a precise Intent Classifier for a Slack Bot.
Your job is to map user natural language queries to a single specific JSON intent.

AVAILABLE INTENTS:
- send_message: Send a new message to a channel or user.
- reply_thread: Reply to a specific thread (requires context, usually explicit instruction).
- create_channel: Create a new channel.
- rename_channel: Rename an existing channel.
- archive_channel: Archive a channel.
- invite_user: Invite a user to a channel.
- remove_user: Remove a user from a channel.
- upload_file: Upload a file (text snippet).
- delete_file: Delete a file.
- list_channels: List available channels.
- list_users: List available users.
- get_history: Get recent messages from a channel.
- add_reaction: Add an emoji reaction to a message.
- remove_reaction: Remove an emoji reaction from a message.
- schedule_message: Schedule a message for later.
- unknown: If the request is unclear or not supported.

RULES:
1. Extract 'channel_name' if mentioned (remove '#').
2. Extract 'user_name' if mentioned (remove '@').
3. Extract 'text' for messages.
4. If user says "add reaction", intent MUST be add_reaction.
5. If user says "remove reaction", intent MUST be remove_reaction.
6. Do NOT classify reaction commands as send_message.
7. Extract 'thread_ts' for reactions if a timestamp is provided.
8. Extract 'reaction_name' (emoji name without colons) for reactions.
9. Return purely valid JSON matching the schema.

SCHEMA:
{format_instructions}
"""

# Create Prompt Template
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{query}")
])

# Create Chain
chain = prompt | llm | parser

def parse_intent(query: str) -> IntentResponse:
    """
    Parses a natural language query into a structured IntentResponse using Groq.
    """
    logger.info(f"Parsing intent for query: {query}")
    try:
        response = chain.invoke({
            "query": query,
            "format_instructions": parser.get_format_instructions()
        })
        logger.info(f"Parsed Intent: {response.intent} | Params: {response.parameters}")
        return response
    except Exception as e:
        logger.error(f"Intent parsing failed: {e}")
        # Fallback to unknown
        return IntentResponse(
            intent="unknown", 
            reflection=f"Parsing error: {str(e)}", 
            parameters={}
        )
