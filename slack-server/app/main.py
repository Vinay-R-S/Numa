
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from app.intent_parser import parse_intent
from app.slack_router import router
from app.config import settings
from app.monitor.scheduler import start_scheduler, stop_scheduler

# Logging
logger = logging.getLogger("api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    stop_scheduler()

# Initialize FastAPI with lifespan
app = FastAPI(title="Slack Automation Backend", version="3.0.0", lifespan=lifespan)

# ----------------------------
# Schemas
# ----------------------------

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    intent: str
    debug_info: dict

# ----------------------------
# Health Check
# ----------------------------

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "slack-automation-backend"}

# ----------------------------
# Chat Endpoint (Single Pass)
# ----------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    1. Parse Intent (LLM)
    2. Execute Action (Python/Slack SDK)
    3. Return Result
    """
    try:
        logger.info(f"Received message: {request.message}")

        # Step 1: Parse Intent
        intent_data = parse_intent(request.message)
        logger.info(f"Parsed Intent: {intent_data.intent}")

        # Step 2: Execute Action
        result = router.execute(intent_data)
        logger.info(f"Execution Result: {result}")

        # Step 3: Format Response
        if result.get("ok"):
            text_response = result.get("message") or str(result)
        else:
            text_response = f"Error: {result.get('error')}"

        return ChatResponse(
            response=text_response,
            intent=intent_data.intent,
            debug_info=result
        )

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True)
