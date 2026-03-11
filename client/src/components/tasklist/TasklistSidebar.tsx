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
  PanelLeftClose,
  PanelLeft,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"

const NAV_ITEMS = [
  { href: "/home", icon: Home, label: "Home" },
  { href: "/tasklist", icon: CheckSquare, label: "Task List" },
  { href: "/home", icon: LayoutDashboard, label: "Dashboard", disabled: true },
  { href: "/home", icon: Zap, label: "Agents", disabled: true },
  { href: "/home", icon: Settings, label: "Settings", disabled: true },
]

interface TasklistSidebarProps {
  isOpen: boolean
  collapsed: boolean
  onClose: () => void
  onToggleCollapse: () => void
}

export function TasklistSidebar({ isOpen, collapsed, onClose, onToggleCollapse }: TasklistSidebarProps) {
  const pathname = usePathname()

  const handleSignOut = () => {
    localStorage.removeItem("numa_token")
    window.location.href = "/auth"
  }

  return (
    <aside
      className={cn(
        // Base layout
        "flex flex-col border-r border-border/50 bg-sidebar text-sidebar-foreground h-full",
        // Mobile: fixed overlay drawer; Desktop: static in flex flow
        "fixed inset-y-0 left-0 z-30 transition-transform",
        "lg:static lg:inset-auto lg:z-auto lg:translate-x-0 lg:transition-none",
        // Mobile open/close
        isOpen ? "translate-x-0" : "-translate-x-full",
        // Width: collapse only works on desktop
        collapsed ? "lg:w-14" : "lg:w-56",
        // Mobile always full width
        "w-64 lg:w-auto"
      )}
    >
      {/* Header */}
      <div className="relative flex h-14 items-center border-b border-border/50 shrink-0 px-4">
        {/* Logo — always centered */}
        <div className="flex flex-1 items-center justify-center">
          {collapsed ? (
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-primary/30 to-primary/10 ring-1 ring-primary/20 shadow-sm">
              <Zap className="h-4 w-4 text-primary fill-primary/20" />
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary/30 to-primary/10 ring-1 ring-primary/20 shadow-sm">
                <Zap className="h-4 w-4 text-primary fill-primary/20" />
              </div>
              <span className="font-bold text-sm tracking-tight text-foreground">NUMA</span>
            </div>
          )}
        </div>

        {/* Desktop collapse toggle — absolute right */}
        <button
          type="button"
          onClick={onToggleCollapse}
          className="hidden lg:flex absolute right-3 items-center justify-center rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent border border-transparent hover:border-border/60 transition-all"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
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
      <nav className="flex-1 overflow-auto px-3 py-4 space-y-0.5">
        {!collapsed && (
          <p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1 lg:block hidden">
            Navigation
          </p>
        )}
        <p className={cn("px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1 lg:hidden")}>
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
                else onClose()           // close mobile drawer on navigation
              }}
              title={collapsed ? label : undefined}
              className={cn(
                "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-all",
                collapsed ? "lg:justify-center lg:px-2" : "gap-3",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                disabled && "opacity-40 cursor-not-allowed"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className={cn("flex-1 truncate", collapsed && "lg:hidden")}>{label}</span>
              {active && !collapsed && <ChevronRight className="h-3.5 w-3.5 opacity-60 lg:block hidden" />}
              {active && <ChevronRight className="h-3.5 w-3.5 opacity-60 lg:hidden" />}
              {disabled && !collapsed && (
                <span className="lg:block hidden text-[9px] font-medium rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground">
                  Soon
                </span>
              )}
              {disabled && (
                <span className="lg:hidden text-[9px] font-medium rounded-full bg-muted px-1.5 py-0.5 text-muted-foreground">
                  Soon
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border/50 p-3 shrink-0">
        <button
          onClick={handleSignOut}
          title={collapsed ? "Sign Out" : undefined}
          className={cn(
            "flex w-full items-center rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive",
            collapsed ? "lg:justify-center lg:px-2 gap-3" : "gap-3"
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span className={cn(collapsed && "lg:hidden")}>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
