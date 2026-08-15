/**
 * Productivity constants (NUMA-117 P4, PLAN 21.2).
 *
 * Storage keys, list caps and the data-driven card/bar definitions the sections
 * render, extracted from the hand-written JSX in `productivity/page.tsx`.
 */
import { Code2, GitFork, GitPullRequest } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import type { GitHubStats, LeetCodeStats } from "./productivity.types"

/** Shared with `settings/page.tsx`, which writes the username on save. */
export const LEETCODE_USERNAME_STORAGE_KEY = "numa_leetcode_username"

/** A connect URL that does not start with this is not GitHub's consent screen. */
export const GITHUB_AUTHORIZE_URL_PREFIX = "https://github.com/login/oauth/authorize"

export const RECENT_REPO_LIMIT = 6
export const RECENT_COMMIT_LIMIT = 8
export const RECENT_SUBMISSION_LIMIT = 6

export const ACCEPTED_STATUS = "Accepted"

export interface GitHubStatChip {
  key: string
  icon: LucideIcon
  label: string
  color: string
  value: (stats: GitHubStats | null) => number
}

export const GITHUB_STAT_CHIPS: GitHubStatChip[] = [
  {
    key: "commits-today",
    icon: Code2,
    label: "Commits Today",
    color: "text-emerald-400",
    value: (stats) => stats?.total_commits_today ?? 0,
  },
  {
    key: "commits-week",
    icon: Code2,
    label: "Commits This Week",
    color: "text-cyan-400",
    value: (stats) => stats?.total_commits_week ?? 0,
  },
  {
    key: "open-prs",
    icon: GitPullRequest,
    label: "Open PRs",
    color: "text-purple-400",
    value: (stats) => stats?.open_prs ?? 0,
  },
  {
    key: "total-repos",
    icon: GitFork,
    label: "Total Repos",
    color: "text-amber-400",
    value: (stats) => (stats?.public_repos ?? 0) + (stats?.private_repos ?? 0),
  },
]

export interface LeetCodeDifficultyRow {
  key: string
  label: string
  color: string
  bgColor: string
  solved: (stats: LeetCodeStats) => number
}

export const LEETCODE_DIFFICULTY_ROWS: LeetCodeDifficultyRow[] = [
  {
    key: "easy",
    label: "Easy",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500",
    solved: (stats) => stats.easy_solved,
  },
  {
    key: "medium",
    label: "Medium",
    color: "text-amber-400",
    bgColor: "bg-amber-500",
    solved: (stats) => stats.medium_solved,
  },
  {
    key: "hard",
    label: "Hard",
    color: "text-red-400",
    bgColor: "bg-red-500",
    solved: (stats) => stats.hard_solved,
  },
]
