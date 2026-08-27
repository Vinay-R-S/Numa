"use client"

import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/**
 * The floating dock frame every agent panel sits in (NUMA-118 P4).
 *
 * All four docks used a character-for-character copy of this className. The
 * only difference is where the panel hangs on desktop: the calendar dock sits
 * below the page header (`sm:top-24`), the rest sit at the bottom right.
 */
interface AgentDockShellProps {
  anchor?: "bottom" | "top"
  className?: string
  children: ReactNode
}

const ANCHOR_CLASS = {
  bottom: "sm:bottom-6",
  top: "sm:top-24",
} as const

export function AgentDockShell({ anchor = "bottom", className, children }: AgentDockShellProps) {
  return (
    <section
      className={cn(
        "fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4",
        ANCHOR_CLASS[anchor],
        className
      )}
    >
      {children}
    </section>
  )
}
