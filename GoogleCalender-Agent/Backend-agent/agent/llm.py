"""
LLM Configuration
Configures Groq LLM (Llama 3.3 70B) for the agent
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()


def get_llm():
    """
    Initialize and return the Groq LLM for the agent.
    
    Returns:
        ChatGroq: Configured Groq LLM instance (llama-3.3-70b-versatile)
    """
    api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key or api_key == 'your-groq-api-key-here':
        raise ValueError(
            "Groq API key not configured. "
            "Please set GROQ_API_KEY in .env file"
        )
    
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        api_key=api_key
    )
    
    return llm
