"use client"

import React from "react"
import { cn } from "@/lib/utils"

interface StatCardProps {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
  href?: string
  iconColor?: string
}

export const StatCard = React.memo(function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  href,
  iconColor,
}: StatCardProps) {
  const inner = (
    <div
      className={cn(
        "rounded-xl border border-border/40 bg-card/40 p-4 transition-all",
        href && "hover:bg-accent/30 hover:border-border/60 cursor-pointer"
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <Icon className={cn("h-4 w-4", iconColor || "text-muted-foreground")} />
      </div>
      <p className="text-2xl font-bold text-foreground sm:text-3xl tabular-nums">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </div>
  )

  if (href) {
    return (
      <a href={href} className="block">
        {inner}
      </a>
    )
  }
  return inner
})
