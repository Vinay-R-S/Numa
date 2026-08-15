import { RECENT_COMMIT_LIMIT } from "../productivity.constants"
import type { GitHubCommit } from "../productivity.types"
import { commitDateLabel } from "../productivity.utils"

export function RecentCommitsList({ commits }: { commits: GitHubCommit[] }) {
  if (commits.length === 0) return null

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
        Recent Commits
      </h4>
      <div className="space-y-1.5">
        {commits.slice(0, RECENT_COMMIT_LIMIT).map((commit) => (
          <a
            key={`${commit.repo}-${commit.sha}`}
            href={commit.html_url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="group block rounded-lg border border-border/30 bg-background/30 px-3 py-2.5 transition-colors hover:border-border/60 hover:bg-background/60"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 truncate text-sm font-semibold text-foreground">
                {commit.message || "Commit"}
              </p>
              <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                {commit.sha}
              </span>
            </div>
            <p className="mt-1 truncate text-[11px] text-muted-foreground">
              {commit.repo}
              {commitDateLabel(commit.date)}
            </p>
          </a>
        ))}
      </div>
    </div>
  )
}
