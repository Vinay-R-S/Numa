import { cn } from "@/lib/utils"

import { solvedPercentage } from "../productivity.utils"

export function DifficultyBar({
  label,
  solved,
  total,
  color,
  bgColor,
}: {
  label: string
  solved: number
  total: number
  color: string
  bgColor: string
}) {
  const pct = solvedPercentage(solved, total)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className={cn("text-xs font-semibold", color)}>{label}</span>
        <span className="text-xs text-muted-foreground tabular-nums">
          {solved} <span className="text-muted-foreground/50">/ {total}</span>
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-border/20 overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", bgColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
