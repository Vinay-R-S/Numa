"use client"

import React, { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  CheckSquare,
  Home,
  CalendarDays,
  Leaf,
  Zap,
  Settings,
  LogOut,
  ChevronRight,
  Pin,
  PinOff,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { href: "/home", icon: Home, label: "Home" },
  { href: "/tasklist", icon: CheckSquare, label: "Task List" },
  { href: "/calendar", icon: CalendarDays, label: "Calendar" },
  { href: "/mental-peace", icon: Leaf, label: "Mental Peace" },
  { href: "/home", icon: LayoutDashboard, label: "Dashboard", disabled: true },
  { href: "/home", icon: Zap, label: "Agents", disabled: true },
  { href: "/settings", icon: Settings, label: "Settings" },
]

interface TasklistSidebarProps {
  isOpen: boolean
  locked: boolean
  onClose: () => void
  onToggleLock: () => void
}

export function TasklistSidebar({ isOpen, locked, onClose, onToggleLock }: TasklistSidebarProps) {
  const pathname = usePathname()
  // Desktop hover-to-expand state — only matters when not locked
  const [hovered, setHovered] = useState(false)
  const isExpanded = locked || hovered

  const handleSignOut = () => {
    localStorage.removeItem("numa_token")
    window.location.href = "/auth"
  }

  return (
    <aside
      onMouseEnter={() => { if (!locked) setHovered(true) }}
      onMouseLeave={() => { if (!locked) setHovered(false) }}
      className={cn(
        // Base layout
        "flex flex-col border-r border-border/50 bg-sidebar text-sidebar-foreground h-full",
        // Mobile: fixed overlay drawer
        "fixed inset-y-0 left-0 z-30 transition-transform",
        isOpen ? "translate-x-0" : "-translate-x-full",
        // Desktop: when locked → static in flex flow; when unlocked → fixed overlay so content never shifts
        "lg:translate-x-0",
        locked ? "lg:static lg:inset-auto lg:z-auto" : "lg:fixed lg:inset-y-0 lg:left-0 lg:z-40",
        // Width — smooth transition on desktop
        "w-64 lg:transition-[width] lg:duration-200 lg:ease-in-out",
        isExpanded ? "lg:w-56" : "lg:w-14",
      )}
    >
      {/* Header */}
      <div className="relative flex h-14 items-center border-b border-border/50 shrink-0 px-3">
        {/* Logo */}
        <div className="flex flex-1 items-center justify-center overflow-hidden">
          {!isExpanded ? (
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-linear-to-br from-primary/30 to-primary/10 ring-1 ring-primary/20 shadow-sm">
              <Zap className="h-4 w-4 text-primary fill-primary/20" />
            </div>
          ) : (
            <div className="flex items-center gap-2 w-full pl-1">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-linear-to-br from-primary/30 to-primary/10 ring-1 ring-primary/20 shadow-sm">
                <Zap className="h-4 w-4 text-primary fill-primary/20" />
              </div>
              <span className="font-bold text-sm tracking-tight text-foreground whitespace-nowrap">NUMA</span>
            </div>
          )}
        </div>

        {/* Desktop lock/pin toggle — absolute right */}
        <button
          type="button"
          onClick={onToggleLock}
          className={cn(
            "hidden lg:flex absolute right-2 items-center justify-center rounded-md p-1.5 transition-all border border-transparent",
            locked
              ? "text-primary bg-primary/10 border-primary/20 hover:bg-primary/20"
              : "text-muted-foreground hover:text-foreground hover:bg-accent hover:border-border/60",
            !isExpanded && "opacity-0 pointer-events-none",
          )}
          title={locked ? "Unpin sidebar (hover to expand)" : "Pin sidebar open"}
          aria-label={locked ? "Unpin sidebar" : "Pin sidebar"}
        >
          {locked ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
        </button>

        {/* Mobile close button — absolute right */}
        <button
          type="button"
          onClick={onClose}
          className="lg:hidden absolute right-3 flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          aria-label="Close navigation"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-auto px-2 py-4 space-y-0.5">
        <p className={cn(
          "px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1 whitespace-nowrap",
          !isExpanded && "lg:hidden"
        )}>
          Navigation
        </p>

        {NAV_ITEMS.map(({ href, icon: Icon, label, disabled }) => {
          const active = pathname === href
          return (
            <Link
              key={label}
              href={disabled ? "#" : href}
              onClick={(e) => {
                if (disabled) e.preventDefault()
                else onClose()
              }}
              title={!isExpanded ? label : undefined}
              className={cn(
                "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-all gap-3",
                !isExpanded && "lg:justify-center lg:px-2",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                disabled && "opacity-40 cursor-not-allowed"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className={cn(
                "flex-1 truncate whitespace-nowrap transition-opacity duration-150",
                !isExpanded ? "lg:hidden" : "lg:inline"
              )}>{label}</span>
              {active && (
                <ChevronRight className={cn("h-3.5 w-3.5 opacity-60", !isExpanded && "lg:hidden")} />
              )}
              {disabled && (
                <span className={cn(
                  "text-[9px] font-medium rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground whitespace-nowrap",
                  !isExpanded && "lg:hidden"
                )}>
                  Soon
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border/50 p-2 shrink-0">
        <button
          onClick={handleSignOut}
          title={!isExpanded ? "Sign Out" : undefined}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive",
            !isExpanded ? "lg:justify-center lg:px-2" : ""
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span className={cn("whitespace-nowrap", !isExpanded && "lg:hidden")}>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
