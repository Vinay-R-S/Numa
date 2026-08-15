import { Code2 } from "lucide-react"

export function ProductivityPageHeader() {
  return (
    <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
          <Code2 className="h-5 w-5 text-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
            Productivity
          </h1>
          <p className="text-xs text-muted-foreground sm:text-sm">
            Track your GitHub contributions and LeetCode progress
          </p>
        </div>
      </div>
    </header>
  )
}
