import type { ElementType, ReactNode } from "react"

export function ProductivityPanel({
  icon: Icon,
  title,
  children,
}: {
  icon: ElementType
  title: string
  children: ReactNode
}) {
  return (
    <section className="flex flex-col rounded-2xl border border-border/40 bg-card/40 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-border/40 px-5 py-3.5 shrink-0">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-muted/30 ring-1 ring-border/40">
          <Icon className="h-4 w-4 text-foreground" />
        </div>
        <span className="text-sm font-semibold text-foreground">{title}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-5">{children}</div>
    </section>
  )
}
