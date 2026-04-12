"use client"

import React, { useState, useEffect, useCallback } from "react"
import { Menu, Zap } from "lucide-react"
import { TasklistSidebar } from "@/components/tasklist/TasklistSidebar"

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // locked = sidebar is pinned open on desktop; false = hover-to-expand only
  const [locked, setLocked] = useState(false)

  // Persist pin state across page navigations
  useEffect(() => {
    const saved = localStorage.getItem("numa_sidebar_locked")
    if (saved === "true") setLocked(true)
  }, [])

  const handleToggleLock = useCallback(() => {
    setLocked((l) => {
      const next = !l
      localStorage.setItem("numa_sidebar_locked", String(next))
      return next
    })
  }, [])

  return (
    <div className="dark flex h-screen overflow-hidden bg-background text-foreground">
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <TasklistSidebar
        isOpen={sidebarOpen}
        locked={locked}
        onClose={() => setSidebarOpen(false)}
        onToggleLock={handleToggleLock}
      />

      {/* On desktop when not locked, the sidebar is fixed-overlay so we need a spacer to reserve the rail width */}
      {!locked && <div className="hidden lg:block lg:w-14 shrink-0" />}

      <main className="relative flex-1 overflow-y-auto min-w-0">
        {/* Mobile-only topbar with hamburger */}
        <div className="sticky top-0 z-10 flex items-center h-12 px-4 border-b border-border/50 bg-background/95 backdrop-blur-sm lg:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="ml-3 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-linear-to-br from-primary/30 to-primary/10 ring-1 ring-primary/20 shadow-sm">
              <Zap className="h-3.5 w-3.5 text-primary fill-primary/20" />
            </div>
            <span className="text-sm font-bold tracking-tight">NUMA</span>
          </div>
        </div>

        {children}
      </main>
    </div>
  )
}
