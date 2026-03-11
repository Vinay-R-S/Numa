"use client"

import React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  CheckSquare,
  Home,
  Zap,
  Settings,
  LogOut,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { href: "/home", icon: Home, label: "Home" },
  { href: "/tasklist", icon: CheckSquare, label: "Task List" },
  { href: "/home", icon: LayoutDashboard, label: "Dashboard", disabled: true },
  { href: "/home", icon: Zap, label: "Agents", disabled: true },
  { href: "/home", icon: Settings, label: "Settings", disabled: true },
]

export function TasklistSidebar() {
  const pathname = usePathname()

  const handleSignOut = () => {
    localStorage.removeItem("numa_token")
    window.location.href = "/auth"
  }

  return (
    <aside className="flex h-full w-56 flex-col border-r border-border/50 bg-sidebar text-sidebar-foreground">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 px-5 border-b border-border/50">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
          <Zap className="h-4 w-4 text-primary" />
        </div>
        <span className="font-semibold text-sm tracking-tight text-foreground">NUMA</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-auto px-3 py-4 space-y-0.5">
        <p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1">
          Navigation
        </p>
        {NAV_ITEMS.map(({ href, icon: Icon, label, disabled }) => {
          const active = pathname === href
          return (
            <Link
              key={label}
              href={disabled ? "#" : href}
              onClick={disabled ? (e) => e.preventDefault() : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                disabled && "opacity-40 cursor-not-allowed"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight className="h-3.5 w-3.5 opacity-60" />}
              {disabled && (
                <span className="text-[9px] font-medium rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground">
                  Soon
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border/50 p-3">
        <button
          onClick={handleSignOut}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
