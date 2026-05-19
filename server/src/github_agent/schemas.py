from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class GitHubConnectResponse(BaseModel):
    authorization_url: str


class GitHubAuthStatus(BaseModel):
    connected: bool
    github_username: Optional[str] = None
    avatar_url: Optional[str] = None
    scope: Optional[str] = None


class GitHubTokenConnectRequest(BaseModel):
    access_token: str


class GitHubUserStats(BaseModel):
    username: str
    avatar_url: Optional[str] = None
    public_repos: int = 0
    private_repos: int = 0
    followers: int = 0
    following: int = 0
    total_commits_today: int = 0
    total_commits_week: int = 0
    open_prs: int = 0
    recent_repos: list[dict] = []
    recent_commits: list[dict] = []


class GitHubChatMessage(BaseModel):
    role: str
    content: str


class GitHubChatRequest(BaseModel):
    query: str
    history: list[GitHubChatMessage] = []


class GitHubChatResponse(BaseModel):
    response: str
    success: bool
    delegated_to: str = "github-subagent"
    refresh_github: bool = False
