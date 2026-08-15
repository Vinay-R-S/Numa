import { Trophy } from "lucide-react"

export function LeetCodeEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-10">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 ring-1 ring-amber-500/20">
        <Trophy className="h-7 w-7 text-amber-400" />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-foreground">Track your LeetCode</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Add your LeetCode username in{" "}
          <a
            href="/settings"
            className="text-primary underline underline-offset-2 hover:text-primary/80"
          >
            Settings → Integration Keys
          </a>
          {" "}to see your progress
        </p>
      </div>
    </div>
  )
}
