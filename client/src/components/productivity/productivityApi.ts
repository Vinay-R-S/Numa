/**
 * Productivity API client - GitHub + LeetCode tracking
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {}
  const token = localStorage.getItem("numa_token")
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

// ── GitHub Types ────────────────────────────────────────────────────────────────

export interface GitHubAuthStatus {
  connected: boolean
  github_username?: string
  avatar_url?: string
  scope?: string
}

export interface GitHubRepo {
  name: string
  full_name: string
  private: boolean
  language?: string
  stars: number
  forks: number
  updated_at?: string
  html_url?: string
}

export interface GitHubCommit {
  sha: string
  message: string
  repo: string
  author?: string
  date?: string
  html_url?: string
}

export interface GitHubStats {
  username: string
  avatar_url?: string
  public_repos: number
  private_repos: number
  followers: number
  following: number
  total_commits_today: number
  total_commits_week: number
  open_prs: number
  recent_repos: GitHubRepo[]
  recent_commits: GitHubCommit[]
}

// ── LeetCode Types ──────────────────────────────────────────────────────────────

export interface LeetCodeSubmission {
  title: string
  timestamp: string
  status: string
  lang: string
}

export interface LeetCodeStats {
  username: string
  total_solved: number
  easy_solved: number
  medium_solved: number
  hard_solved: number
  acceptance_rate: number
  ranking: number
  recent_submissions: LeetCodeSubmission[]
}

// ── GitHub API ──────────────────────────────────────────────────────────────────

export async function getGitHubStatus(): Promise<GitHubAuthStatus> {
  const res = await fetch(`${API_BASE}/api/github/status`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to fetch GitHub status")
  return res.json()
}

export async function connectGitHub(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/github/connect`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to get GitHub auth URL")
  const data = await res.json()
  const authorizationUrl = data.authorization_url
  if (typeof authorizationUrl !== "string" || !authorizationUrl.startsWith("https://github.com/login/oauth/authorize")) {
    throw new Error("Invalid GitHub authorization URL")
  }
  return authorizationUrl
}

export async function connectGitHubToken(accessToken: string): Promise<GitHubAuthStatus> {
  const res = await fetch(`${API_BASE}/api/github/connect-token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ access_token: accessToken }),
  })
  if (!res.ok) throw await parseError(res, "Failed to connect GitHub token")
  return res.json()
}

export async function getGitHubStats(): Promise<GitHubStats> {
  const res = await fetch(`${API_BASE}/api/github/stats`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to fetch GitHub stats")
  return res.json()
}

export async function disconnectGitHub(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/github/disconnect`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to disconnect GitHub")
}

// ── LeetCode API ────────────────────────────────────────────────────────────────

export async function getLeetCodeStats(username: string): Promise<LeetCodeStats> {
  const res = await fetch(
    `${API_BASE}/api/leetcode/stats?username=${encodeURIComponent(username)}`,
    { headers: getAuthHeaders() },
  )
  if (!res.ok) throw new Error("Failed to fetch LeetCode stats")
  return res.json()
}

async function parseError(response: Response, fallbackMessage: string): Promise<Error> {
  try {
    const body = await response.json()
    if (typeof body?.detail === "string" && body.detail.trim()) {
      return new Error(body.detail)
    }
  } catch {
    // ignore non-JSON response bodies
  }

  return new Error(fallbackMessage)
}
