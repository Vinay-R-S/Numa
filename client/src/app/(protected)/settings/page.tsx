"use client"

import { useState } from "react"
import { Bot, Cpu, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { AiModelPreset, getAiSettings, setAiSettings } from "@/lib/aiSettings"

export default function SettingsPage() {
  const [enabled, setEnabled] = useState(() => getAiSettings().enabled)
  const [modelPreset, setModelPreset] = useState<AiModelPreset>(() => getAiSettings().modelPreset)

  const handleToggleAi = () => {
    const updated = setAiSettings({ enabled: !enabled })
    setEnabled(updated.enabled)
  }

  const handleModelChange = (preset: AiModelPreset) => {
    const updated = setAiSettings({ modelPreset: preset })
    setModelPreset(updated.modelPreset)
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col gap-4 px-3 py-4 sm:gap-6 sm:px-6 sm:py-6">
      <header className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">Settings</h1>
        <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
          Configure AI agent behavior and model presets for Calendar and Master Agent.
        </p>
      </header>

      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Bot className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">AI Agent Toggle</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Turn agent features on or off without changing backend config.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-background/40 px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-4">
          <div className="text-sm text-foreground">
            Agent status: <span className={cn("font-semibold", enabled ? "text-emerald-400" : "text-rose-400")}>{enabled ? "Enabled" : "Disabled"}</span>
          </div>
          <Button type="button" variant={enabled ? "outline" : "default"} size="sm" className="w-full sm:w-auto" onClick={handleToggleAi}>
            {enabled ? "Disable Agents" : "Enable Agents"}
          </Button>
        </div>
      </section>

      <section className="rounded-xl border border-border/40 bg-card/40 p-4 sm:rounded-2xl sm:p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20 sm:h-9 sm:w-9">
            <Cpu className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground sm:text-lg">Groq Model Preset</h2>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Choose the default inference size used by Calendar and Master Agent chats.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => handleModelChange("70b")}
            className={cn(
              "rounded-xl border px-3 py-3 text-left transition-all sm:px-4 sm:py-4",
              modelPreset === "70b"
                ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
                : "border-border/40 bg-background/40 hover:bg-accent/40"
            )}
          >
            <div className="mb-1 flex items-center gap-2 text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="font-semibold">70B</span>
            </div>
            <p className="text-xs text-muted-foreground sm:text-sm">Higher quality reasoning, slower and costlier.</p>
          </button>

          <button
            type="button"
            onClick={() => handleModelChange("8b")}
            className={cn(
              "rounded-xl border px-3 py-3 text-left transition-all sm:px-4 sm:py-4",
              modelPreset === "8b"
                ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
                : "border-border/40 bg-background/40 hover:bg-accent/40"
            )}
          >
            <div className="mb-1 flex items-center gap-2 text-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="font-semibold">8B</span>
            </div>
            <p className="text-xs text-muted-foreground sm:text-sm">Faster responses and lower cost for lightweight tasks.</p>
          </button>
        </div>
      </section>
    </div>
  )
}
