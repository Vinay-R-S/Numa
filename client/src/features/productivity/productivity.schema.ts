/**
 * Productivity validation schemas (NUMA-117 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the Pydantic DTOs in `server/src/github_agent/schemas.py` and
 * `server/src/leetcode/schemas.py`. Response schemas run through the shared
 * `http` `schema` option so contract drift fails loudly instead of rendering
 * `undefined`; the input schema mirrors `GitHubTokenConnectRequest`.
 *
 * Repos, commits and submissions are `list[dict]` on the server (no
 * `response_model` filtering), and each of the two GitHub paths - the live API
 * fetch and the Postgres cache read - emits a different superset of keys. They
 * are `looseObject` so the extra keys survive, with only the rendered fields
 * required. Timestamps stay strings: the UI formats them itself.
 */
import { z } from "@/lib/validation"
import type {
  GitHubAuthStatus,
  GitHubCommit,
  GitHubRepo,
  GitHubStats,
  IntegrationKeys,
  LeetCodeStats,
  LeetCodeSubmission,
} from "./productivity.types"

export const githubAuthStatusSchema: z.ZodType<GitHubAuthStatus> = z.object({
  connected: z.boolean(),
  github_username: z.string().nullish(),
  avatar_url: z.string().nullish(),
  scope: z.string().nullish(),
})

export const githubConnectResponseSchema = z.object({
  authorization_url: z.string(),
})

export const githubRepoSchema: z.ZodType<GitHubRepo> = z.looseObject({
  name: z.string(),
  full_name: z.string(),
  private: z.boolean(),
  language: z.string().nullish(),
  stars: z.number(),
  forks: z.number(),
  updated_at: z.string().nullish(),
  html_url: z.string().nullish(),
})

export const githubCommitSchema: z.ZodType<GitHubCommit> = z.looseObject({
  sha: z.string(),
  message: z.string(),
  repo: z.string(),
  author: z.string().nullish(),
  date: z.string().nullish(),
  html_url: z.string().nullish(),
})

export const githubStatsSchema: z.ZodType<GitHubStats> = z.object({
  username: z.string(),
  avatar_url: z.string().nullish(),
  public_repos: z.number(),
  private_repos: z.number(),
  followers: z.number(),
  following: z.number(),
  total_commits_today: z.number(),
  total_commits_week: z.number(),
  open_prs: z.number(),
  recent_repos: z.array(githubRepoSchema),
  recent_commits: z.array(githubCommitSchema),
})

export const leetCodeSubmissionSchema: z.ZodType<LeetCodeSubmission> = z.looseObject({
  title: z.string(),
  timestamp: z.union([z.string(), z.number()]),
  status: z.string(),
  lang: z.string(),
})

export const leetCodeStatsSchema: z.ZodType<LeetCodeStats> = z.object({
  username: z.string(),
  total_solved: z.number(),
  easy_solved: z.number(),
  medium_solved: z.number(),
  hard_solved: z.number(),
  acceptance_rate: z.number(),
  ranking: z.number(),
  contribution_points: z.number(),
  reputation: z.number(),
  recent_submissions: z.array(leetCodeSubmissionSchema),
})

/** Loose: the route returns one boolean per configured key alongside the values. */
export const integrationKeysSchema: z.ZodType<IntegrationKeys> = z.looseObject({
  leetcode_username_value: z.string().optional(),
})

/** Input schema for the token connect form; mirrors `GitHubTokenConnectRequest`. */
export const githubTokenConnectSchema = z.object({
  access_token: z.string().trim().min(1, "Paste a GitHub token first"),
})

export type GitHubTokenConnectInput = z.infer<typeof githubTokenConnectSchema>
