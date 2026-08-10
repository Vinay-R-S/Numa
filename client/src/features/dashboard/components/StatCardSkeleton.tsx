export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="h-3 w-16 rounded bg-muted/50" />
        <div className="h-4 w-4 rounded bg-muted/50" />
      </div>
      <div className="h-8 w-12 rounded bg-muted/50" />
      <div className="mt-1 h-3 w-20 rounded bg-muted/30" />
    </div>
  )
}
