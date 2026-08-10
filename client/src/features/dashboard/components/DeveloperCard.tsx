"use client"

import { Code2, GitBranch } from "lucide-react"
import { cn } from "@/lib/utils"
import { ICON_COLORS } from "../dashboard.constants"
import type { DashboardGithub } from "../dashboard.types"

export function DeveloperCard({ github }: { github: DashboardGithub }) {
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Code2 className={cn("h-4 w-4", ICON_COLORS.github)} />
          <span className="text-sm font-semibold text-foreground">Developer</span>
        </div>
        <a href="/productivity" className="text-xs text-muted-foreground hover:text-foreground">
          View all
        </a>
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-3 rounded-lg bg-background/40 px-3 py-2">
          <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs text-foreground">
            GitHub:{" "}
            {github.connected ? (
              <span className="text-emerald-400 font-medium">@{github.username}</span>
            ) : (
              <span className="text-muted-foreground">Not connected</span>
            )}
          </span>
        </div>
      </div>
    </div>
  )
}
