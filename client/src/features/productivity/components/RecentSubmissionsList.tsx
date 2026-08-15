import { cn } from "@/lib/utils"

import { ACCEPTED_STATUS, RECENT_SUBMISSION_LIMIT } from "../productivity.constants"
import type { LeetCodeSubmission } from "../productivity.types"

export function RecentSubmissionsList({ submissions }: { submissions: LeetCodeSubmission[] }) {
  if (submissions.length === 0) return null

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
        Recent Submissions
      </h4>
      <div className="space-y-1.5">
        {submissions.slice(0, RECENT_SUBMISSION_LIMIT).map((submission, index) => {
          const accepted = submission.status === ACCEPTED_STATUS

          return (
            <div
              // The same problem can be accepted twice, and LeetCode may omit
              // the timestamp, so the position disambiguates an otherwise
              // identical pair. The list never reorders in place.
              key={`${submission.title}-${submission.timestamp}-${index}`}
              className="flex items-center gap-3 rounded-lg border border-border/30 bg-background/30 px-3 py-2.5"
            >
              <div
                className={cn(
                  "h-2 w-2 shrink-0 rounded-full",
                  accepted ? "bg-emerald-500" : "bg-red-500"
                )}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground truncate">{submission.title}</p>
                <p className="text-[11px] text-muted-foreground">
                  {submission.lang} &middot; {submission.timestamp}
                </p>
              </div>
              <span
                className={cn(
                  "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold",
                  accepted ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                )}
              >
                {submission.status}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
