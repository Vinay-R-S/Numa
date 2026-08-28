"use client"

import { ChevronDown, Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

/**
 * Model dropdown. The list is the provider's catalogue, or the locally pulled
 * Ollama models when there are any, so the two hints below it are the Ollama
 * lookup's empty and pending states.
 */
export function ModelSelect({
  selectedModel,
  options,
  open,
  canOpen,
  ollamaEmpty,
  ollamaLoading,
  onToggle,
  onSelect,
}: {
  selectedModel: string
  options: string[]
  open: boolean
  canOpen: boolean
  ollamaEmpty: boolean
  ollamaLoading: boolean
  onToggle: () => void
  onSelect: (model: string) => void
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Model</label>
      <div className="relative">
        <button
          type="button"
          onClick={onToggle}
          className="flex w-full items-center justify-between rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent/40"
        >
          <span className="truncate">{selectedModel || "Select model"}</span>
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-180"
            )}
          />
        </button>
        {open && canOpen && (
          <div className="absolute z-20 mt-1 w-full rounded-lg border border-border/60 bg-card shadow-lg">
            <div className="max-h-48 overflow-y-auto py-1">
              {options.map((model) => (
                <button
                  key={model}
                  type="button"
                  className={cn(
                    "w-full px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent/40",
                    model === selectedModel
                      ? "bg-primary/10 font-medium text-primary"
                      : "text-foreground"
                  )}
                  onClick={() => onSelect(model)}
                >
                  {model}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      {ollamaEmpty && (
        <p className="mt-1 text-[10px] text-muted-foreground">
          No local models found. Make sure Ollama is running.
        </p>
      )}
      {ollamaLoading && (
        <p className="mt-1 text-[10px] text-muted-foreground flex items-center gap-1">
          <Loader2 className="h-3 w-3 animate-spin" /> Loading models...
        </p>
      )}
    </div>
  )
}
