"use client"

/**
 * Quick-action chips above a dock's transcript (NUMA-118 P4).
 *
 * Extracted from the identical row in the slack and health panels. Chips
 * prefill the composer, they never send: they drive mutating tools, so the user
 * reviews the text first.
 *
 * `idPrefix` reproduces the per-chip ids the slack panel carried. The slack
 * chips also had no explicit `type`, which defaults to "submit"; they sit
 * outside any form so it never mattered, and both now carry `type="button"`
 * like the health copy.
 */
interface AgentSuggestionChipsProps {
  suggestions: readonly string[]
  idPrefix?: string
  onSelect: (suggestion: string) => void
}

export function AgentSuggestionChips({
  suggestions,
  idPrefix,
  onSelect,
}: AgentSuggestionChipsProps) {
  return (
    <div className="border-b border-border/20 px-1 py-2 shrink-0">
      <div className="flex flex-wrap gap-1.5">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            id={idPrefix ? `${idPrefix}-${suggestion.replace(/\s+/g, "-").toLowerCase()}` : undefined}
            type="button"
            onClick={() => onSelect(suggestion)}
            className="rounded-full border border-border/40 bg-background/40 px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-foreground"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
