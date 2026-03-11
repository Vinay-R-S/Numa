"use client"

import * as React from "react"
import { ScrollArea } from "radix-ui"
import { cn } from "@/lib/utils"

const ScrollAreaRoot = React.forwardRef<
  React.ComponentRef<typeof ScrollArea.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollArea.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollArea.Root
    ref={ref}
    className={cn("relative overflow-hidden", className)}
    {...props}
  >
    <ScrollArea.Viewport className="h-full w-full rounded-[inherit]">
      {children}
    </ScrollArea.Viewport>
    <ScrollAreaScrollbar orientation="vertical" />
    <ScrollAreaScrollbar orientation="horizontal" />
    <ScrollArea.Corner />
  </ScrollArea.Root>
))
ScrollAreaRoot.displayName = ScrollArea.Root.displayName

const ScrollAreaScrollbar = React.forwardRef<
  React.ComponentRef<typeof ScrollArea.Scrollbar>,
  React.ComponentPropsWithoutRef<typeof ScrollArea.Scrollbar>
>(({ className, orientation = "vertical", ...props }, ref) => (
  <ScrollArea.Scrollbar
    ref={ref}
    orientation={orientation}
    className={cn(
      "flex touch-none select-none transition-colors",
      orientation === "vertical" && "h-full w-2.5 border-l border-l-transparent p-px",
      orientation === "horizontal" && "h-2.5 flex-col border-t border-t-transparent p-px",
      className
    )}
    {...props}
  >
    <ScrollArea.Thumb className="relative flex-1 rounded-full bg-border" />
  </ScrollArea.Scrollbar>
))
ScrollAreaScrollbar.displayName = ScrollArea.Scrollbar.displayName

export { ScrollAreaRoot as ScrollArea, ScrollAreaScrollbar }
