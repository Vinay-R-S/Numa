import { ExternalLink, GitFork, Star } from "lucide-react"

import { RECENT_REPO_LIMIT } from "../productivity.constants"
import type { GitHubRepo } from "../productivity.types"
import { repoUrl } from "../productivity.utils"

export function RecentReposList({ repos }: { repos: GitHubRepo[] }) {
  if (repos.length === 0) return null

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
        Recent Repositories
      </h4>
      <div className="space-y-1.5">
        {repos.slice(0, RECENT_REPO_LIMIT).map((repo) => (
          <a
            key={repo.full_name}
            href={repoUrl(repo.full_name, repo.html_url)}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 rounded-lg border border-border/30 bg-background/30 px-3 py-2.5 transition-colors hover:border-border/60 hover:bg-background/60"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-foreground truncate">{repo.name}</p>
                {repo.private && (
                  <span className="shrink-0 rounded-full border border-border/40 bg-muted/50 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                    Private
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex items-center gap-3 text-[11px] text-muted-foreground">
                {repo.language && (
                  <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-primary/60" />
                    {repo.language}
                  </span>
                )}
                <span className="flex items-center gap-0.5">
                  <Star className="h-3 w-3" /> {repo.stars}
                </span>
                <span className="flex items-center gap-0.5">
                  <GitFork className="h-3 w-3" /> {repo.forks}
                </span>
              </div>
            </div>
            <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40 transition-colors group-hover:text-foreground" />
          </a>
        ))}
      </div>
    </div>
  )
}
