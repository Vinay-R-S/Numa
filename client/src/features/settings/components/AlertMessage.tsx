import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

type AlertTone = "error" | "success" | "warning"

const TONE_CLASSES: Record<AlertTone, string> = {
  error: "border-rose-500/20 bg-rose-500/10 text-rose-400",
  success: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  warning: "border-amber-500/20 bg-amber-500/10 text-amber-400",
}

/** The inline banner the panels repeat for errors, confirmations and reasons. */
export function AlertMessage({
  tone,
  className,
  children,
}: {
  tone: AlertTone
  className?: string
  children: ReactNode
}) {
  return (
    <p className={cn("rounded-lg border px-3 py-2 text-xs", TONE_CLASSES[tone], className)}>
      {children}
    </p>
  )
}
