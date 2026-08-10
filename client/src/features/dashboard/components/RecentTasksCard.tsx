"use client"

import { CheckSquare } from "lucide-react"
import { cn } from "@/lib/utils"
import type { DashboardRecentTask } from "../dashboard.types"

const DOT_CLASS: Record<string, string> = {
  completed: "bg-emerald-400",
  inprogress: "bg-amber-400",
  pending: "bg-rose-400",
}

const BADGE_CLASS: Record<string, string> = {
  completed: "bg-emerald-500/10 text-emerald-400",
  inprogress: "bg-amber-500/10 text-amber-400",
  pending: "bg-rose-500/10 text-rose-400",
}

export function RecentTasksCard({ tasks }: { tasks: DashboardRecentTask[] }) {
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckSquare className="h-4 w-4 text-amber-400" />
          <span className="text-sm font-semibold text-foreground">Recent Tasks</span>
        </div>
        <a href="/tasklist" className="text-xs text-muted-foreground hover:text-foreground">
          View all
        </a>
      </div>
      {tasks.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4 text-center">No tasks yet</p>
      ) : (
        <div className="space-y-1.5">
          {tasks.map((task) => (
            <div
              key={`${task.created_at ?? ""}-${task.title}`}
              className="flex items-center gap-3 rounded-lg bg-background/40 px-3 py-2"
            >
              <div
                className={cn(
                  "h-2.5 w-2.5 shrink-0 rounded-full",
                  DOT_CLASS[task.status] || "bg-blue-400"
                )}
              />
              <span className="flex-1 truncate text-xs font-medium text-foreground">{task.title}</span>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-medium",
                  BADGE_CLASS[task.status] || "bg-blue-500/10 text-blue-400"
                )}
              >
                {task.status}
              </span>
              {task.source_name && (
                <span className="rounded bg-muted/60 px-1.5 py-0.5 text-[9px] text-muted-foreground">
                  {task.source_name}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
