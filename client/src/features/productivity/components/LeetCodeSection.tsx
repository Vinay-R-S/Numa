"use client"

import { Loader2 } from "lucide-react"

import { useLeetCode } from "../useLeetCode"
import { DifficultyBreakdown } from "./DifficultyBreakdown"
import { LeetCodeEmptyState } from "./LeetCodeEmptyState"
import { LeetCodeSummary } from "./LeetCodeSummary"
import { RecentSubmissionsList } from "./RecentSubmissionsList"
import { SectionErrorBanner } from "./SectionErrorBanner"

export function LeetCodeSection() {
  const { username, stats, loading, error } = useLeetCode()

  return (
    <div className="space-y-5">
      {error && <SectionErrorBanner message={error} />}

      {loading && !stats && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {!username && !loading && <LeetCodeEmptyState />}

      {stats && (
        <div className="space-y-5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Tracking:</span>
            <span className="text-xs font-semibold text-foreground">{stats.username}</span>
          </div>

          <LeetCodeSummary stats={stats} />

          <DifficultyBreakdown stats={stats} />

          <RecentSubmissionsList submissions={stats.recent_submissions} />
        </div>
      )}
    </div>
  )
}
