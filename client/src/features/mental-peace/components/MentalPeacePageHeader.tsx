"use client"

import { ArrowLeft, Leaf } from "lucide-react"
import { HeaderActionButton } from "@/components/ui/header-action-button"

interface MentalPeacePageHeaderProps {
  showBack: boolean
  onBack: () => void
}

export function MentalPeacePageHeader({ showBack, onBack }: MentalPeacePageHeaderProps) {
  return (
    <header className="flex shrink-0 flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
          <Leaf className="h-5 w-5 text-foreground" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
            Mental Peace
          </h1>
          <p className="text-xs text-muted-foreground sm:text-sm">
            Stillness, breath, and guided recovery
          </p>
        </div>
      </div>
      {showBack && <HeaderActionButton icon={ArrowLeft} label="Back" onClick={onBack} />}
    </header>
  )
}
