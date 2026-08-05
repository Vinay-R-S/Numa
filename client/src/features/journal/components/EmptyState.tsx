import { BookOpen } from "lucide-react"

export function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
        <BookOpen className="h-8 w-8 text-primary/60" />
      </div>
      <div>
        <h2 className="text-lg font-bold text-foreground mb-1">No entry selected</h2>
        <p className="text-sm text-muted-foreground max-w-xs">
          Select a journal entry from the sidebar, or click &ldquo;New Entry&rdquo; to start writing.
        </p>
      </div>
    </div>
  )
}
