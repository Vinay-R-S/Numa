"use client"

import { CalendarDays } from "lucide-react"

import { Button } from "@/components/ui/button"

interface CalendarConnectPromptProps {
  connecting: boolean
  onConnect: () => void
}

/** Shown when the Google token is missing or expired: a prompt, not an error. */
export function CalendarConnectPrompt({ connecting, onConnect }: CalendarConnectPromptProps) {
  return (
    <div className="shrink-0 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 sm:p-4">
      <div className="mb-2 flex items-center gap-2">
        <CalendarDays className="h-4 w-4 text-amber-400" />
        <p className="text-sm font-medium text-amber-400">Google Calendar not connected</p>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">
        Connect your Google Calendar to sync events, holidays, and birthdays with NUMA.
      </p>
      <Button type="button" variant="outline" size="sm" onClick={onConnect} disabled={connecting}>
        {connecting ? "Redirecting to Google..." : "Connect Google Calendar"}
      </Button>
    </div>
  )
}
