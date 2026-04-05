import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.config import settings
from app.models import IntentResponse

logger = logging.getLogger(__name__)

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    groq_api_key=settings.GROQ_API_KEY,
)

parser = PydanticOutputParser(pydantic_object=IntentResponse)

SYSTEM_PROMPT = """You are the intent classifier for NUMA — a personal productivity assistant integrated with Slack.

AVAILABLE INTENTS:
- send_message         : Send a Slack message to a channel or user
- reply_thread         : Reply to a Slack thread
- create_channel       : Create a new Slack channel
- rename_channel       : Rename a Slack channel
- archive_channel      : Archive a Slack channel
- invite_user          : Invite a user to a channel
- remove_user          : Remove a user from a channel
- upload_file          : Upload a text file/snippet
- list_channels        : List Slack channels
- list_users           : List Slack users
- get_history          : Get recent messages from a channel
- add_reaction         : Add emoji reaction to a message
- remove_reaction      : Remove emoji reaction from a message
- schedule_message     : Schedule a Slack message for later
- task_add             : Add a new task (extracts task_title from text)
- task_list            : List tasks
- plan_today           : Generate / show today's plan
- mood_log             : Log mood (extracts mood and energy level)
- reflect              : Start end-of-day reflection
- score                : Show productivity score
- schedule_view        : Show today's schedule
- unknown              : Request is unclear or not supported

EXTRACTION RULES:
1. For task intents: extract task title into parameters.task_title
2. For mood intents: extract mood (great/good/okay/low/bad) into parameters.mood, energy (1-10) into parameters.energy
3. For messages: extract channel_name (without #) and text
4. For reactions: extract reaction_name (without colons) and thread_ts
5. Return ONLY valid JSON matching the schema exactly

SCHEMA:
{format_instructions}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{query}"),
])

chain = prompt | llm | parser


def parse_intent(query: str) -> IntentResponse:
    logger.info(f"Parsing intent: {query!r}")
    try:
        response = chain.invoke({
            "query": query,
            "format_instructions": parser.get_format_instructions(),
        })
        logger.info(f"Intent: {response.intent}")
        return response
    except Exception as exc:
        logger.error(f"Intent parse error: {exc}")
        return IntentResponse(intent="unknown", reflection=f"Parse error: {exc}")
