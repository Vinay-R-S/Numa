import type { ElementType } from "react"

import { cn } from "@/lib/utils"

export function StatChip({
  icon: Icon,
  label,
  value,
  color = "text-primary",
}: {
  icon: ElementType
  label: string
  value: string | number
  color?: string
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-border/40 bg-background/40 p-3 min-w-0">
      <Icon className={cn("h-4 w-4", color)} />
      <span className="text-lg font-black text-foreground tabular-nums">{value}</span>
      <span className="text-[10px] text-muted-foreground font-medium truncate">{label}</span>
    </div>
  )
}
