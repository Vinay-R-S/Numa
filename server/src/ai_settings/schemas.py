from typing import Optional
from pydantic import BaseModel, Field


class AISettingsUpdate(BaseModel):
    provider: str = Field(..., pattern="^(groq|openai|anthropic|gemini|ollama)$")
    model_id: str
    api_key: Optional[str] = Field(None, description="Plain-text API key; encrypted before storage")
    ollama_base_url: Optional[str] = "http://localhost:11434"
    temperature: float = Field(0.1, ge=0.0, le=2.0)


class AISettingsResponse(BaseModel):
    provider: str
    model_id: str
    has_api_key: bool
    ollama_base_url: Optional[str] = None
    temperature: float


class ProviderInfo(BaseModel):
    id: str
    name: str
    configured_via_env: bool
    models: list[str]
    default_model: str


class ProvidersListResponse(BaseModel):
    providers: list[ProviderInfo]
    current: Optional[AISettingsResponse] = None
