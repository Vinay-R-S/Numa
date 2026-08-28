import type { ReactNode } from "react"
import type { LucideIcon } from "lucide-react"

/**
 * The card shell every settings panel repeats: icon badge, heading, blurb.
 * Extracted from the five hand-written copies in `settings/page.tsx`.
 */
export function SettingsSection({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: LucideIcon
  title: string
  description: ReactNode
  children: ReactNode
}) {
  return (
    <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-foreground sm:text-lg">{title}</h2>
          <p className="text-xs text-muted-foreground sm:text-sm">{description}</p>
        </div>
      </div>
      {children}
    </section>
  )
}
