/**
 * Productivity helpers (NUMA-117 P4, PLAN 21.2). Pure except for the two
 * localStorage accessors, which guard against SSR the way `lib/http` does.
 */
import { LEETCODE_USERNAME_STORAGE_KEY } from "./productivity.constants"
import type { LeetCodeStats } from "./productivity.types"

export function readStoredLeetCodeUsername(): string {
  if (typeof globalThis.localStorage === "undefined") return ""
  return localStorage.getItem(LEETCODE_USERNAME_STORAGE_KEY) || ""
}

export function storeLeetCodeUsername(username: string): void {
  if (typeof globalThis.localStorage === "undefined") return
  localStorage.setItem(LEETCODE_USERNAME_STORAGE_KEY, username)
}

/**
 * Denominator for the difficulty bars. LeetCode reports `total_solved` and the
 * per-difficulty counts separately, so the larger of the two is used to keep a
 * bar from overflowing when they disagree.
 */
export function leetCodeTotalProblems(stats: LeetCodeStats | null): number {
  if (!stats) return 0
  return Math.max(stats.total_solved, stats.easy_solved + stats.medium_solved + stats.hard_solved)
}

export function solvedPercentage(solved: number, total: number): number {
  if (total <= 0) return 0
  return Math.round((solved / total) * 100)
}

export function repoUrl(fullName: string, htmlUrl?: string | null): string {
  return htmlUrl || `https://github.com/${fullName}`
}

export function commitDateLabel(date?: string | null): string {
  if (!date) return ""
  return ` - ${new Date(date).toLocaleDateString()}`
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}
