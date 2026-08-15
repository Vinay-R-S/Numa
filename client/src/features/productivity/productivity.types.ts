/**
 * Productivity domain types (NUMA-117 P4, PLAN 21.2).
 *
 * Mirrors `server/src/github_agent/schemas.py` and
 * `server/src/leetcode/schemas.py`. The two repo/commit/submission collections
 * are `list[dict]` on the server, so only the fields the UI reads are typed here
 * and the schemas keep the rest (see `productivity.schema.ts`).
 */

export interface GitHubAuthStatus {
  connected: boolean
  github_username?: string | null
  avatar_url?: string | null
  scope?: string | null
}

export interface GitHubRepo {
  name: string
  full_name: string
  private: boolean
  language?: string | null
  stars: number
  forks: number
  updated_at?: string | null
  html_url?: string | null
}

export interface GitHubCommit {
  sha: string
  message: string
  repo: string
  author?: string | null
  date?: string | null
  html_url?: string | null
}

export interface GitHubStats {
  username: string
  avatar_url?: string | null
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

export interface LeetCodeSubmission {
  title: string
  /** LeetCode returns an epoch-seconds string; a number is tolerated. */
  timestamp: string | number
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
  contribution_points: number
  reputation: number
  recent_submissions: LeetCodeSubmission[]
}

/**
 * `/ai-settings/integration-keys` answers with one boolean per known key plus
 * `*_value` strings for the non-secret ones. Only the LeetCode username is read
 * here; the rest is carried through untouched.
 */
export interface IntegrationKeys {
  leetcode_username_value?: string
}
