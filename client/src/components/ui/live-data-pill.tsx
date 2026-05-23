"use client"

import { Wifi, WifiOff } from "lucide-react"
import { cn } from "@/lib/utils"

export function LiveDataPill({
  live,
  loading = false,
  configured = true,
  className,
}: {
  live: boolean
  loading?: boolean
  configured?: boolean
  className?: string
}) {
  const Icon = live ? Wifi : WifiOff
  const label = loading ? "Loading" : live ? "Live Data" : configured ? "No Data" : "Not Configured"

  return (
    <div
      className={cn(
        "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-xl border px-3 text-xs font-semibold sm:h-10 sm:px-4",
        live
          ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-400"
          : "border-border/50 bg-card/80 text-muted-foreground",
        className
      )}
    >
      <Icon className={cn("h-3.5 w-3.5", loading && "animate-pulse")} />
      <span className="hidden sm:inline">{label}</span>
    </div>
  )
}
