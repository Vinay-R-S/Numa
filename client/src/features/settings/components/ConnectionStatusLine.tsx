import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

import type { ConnectionStatusLabel } from "../settings.types"

/** "Status: <label>" with the tinted icon, shared by the two OAuth panels. */
export function ConnectionStatusLine({
  status,
  className,
  children,
}: {
  status: ConnectionStatusLabel
  className?: string
  children?: ReactNode
}) {
  const { text, color, Icon, spin } = status

  return (
    <div className={cn("flex items-center gap-2 text-sm text-foreground", className)}>
      <Icon className={cn("h-4 w-4 shrink-0", color, spin && "animate-spin")} />
      <span>
        Status: <span className={cn("font-semibold", color)}>{text}</span>
      </span>
      {children}
    </div>
  )
}
