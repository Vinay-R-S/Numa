"""
FastAPI Application
Main application with agent endpoint
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from agent.graph import agent_graph
import uvicorn


# Initialize FastAPI app
app = FastAPI(
    title="Google Calendar & Gmail Agent API",
    description="LangGraph agent for managing calendar events and emails",
    version="1.0.0"
)


class AgentRequest(BaseModel):
    """Request model for agent endpoint"""
    query: str = Field(..., description="User query to send to the agent")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Schedule a meeting tomorrow at 2pm titled 'Team Sync'"
            }
        }


class AgentResponse(BaseModel):
    """Response model for agent endpoint"""
    response: str
    success: bool


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Google Calendar & Gmail Agent API"
    }


@app.post("/agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Run the LangGraph agent with user query
    
    Args:
        request: AgentRequest with user query
    
    Returns:
        AgentResponse: Agent's response and success status
    """
    try:
        # Extract query from request
        user_query = request.query
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "user_query": user_query
        }
        
        # Run agent graph
        result = agent_graph.invoke(initial_state)
        
        # Extract final response from messages
        messages = result.get('messages', [])
        
        if not messages:
            raise HTTPException(
                status_code=500,
                detail="Agent did not produce any response"
            )
        
        # Get the last AI message
        final_message = messages[-1]
        response_text = final_message.content
        
        return AgentResponse(
            response=response_text,
            success=True
        )
        
    except Exception as e:
        # Log error and return error response
        error_msg = f"Error running agent: {str(e)}"
        print(error_msg)
        
        return AgentResponse(
            response=error_msg,
            success=False
        )


if __name__ == "__main__":
    # Run server
    print("🚀 Starting FastAPI server...")
    print("📝 API Documentation: http://localhost:8000/docs")
    print("🔧 Agent endpoint: POST http://localhost:8000/agent")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
