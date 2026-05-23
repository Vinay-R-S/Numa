"use client"

import React from "react"
import { cn } from "@/lib/utils"

type HeaderActionButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: React.ElementType
  label: string
  active?: boolean
  loading?: boolean
}

export function HeaderActionButton({
  icon: Icon,
  label,
  active = false,
  loading = false,
  className,
  disabled,
  children,
  ...props
}: HeaderActionButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={cn(
        "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-xl border px-3 text-sm font-medium shadow-sm transition-colors",
        "hover:border-border/80 hover:bg-card hover:text-foreground disabled:cursor-not-allowed disabled:opacity-70",
        "sm:h-10 sm:gap-2 sm:px-4",
        active
          ? "border-primary/65 bg-primary/10 text-foreground"
          : "border-border/60 bg-card/95 text-muted-foreground",
        className
      )}
      {...props}
    >
      <Icon className={cn("h-4 w-4", loading && "animate-spin")} />
      <span className="hidden sm:inline">{children ?? label}</span>
    </button>
  )
}
