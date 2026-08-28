"use client"

import { cn } from "@/lib/utils"

import { PROVIDER_DESCRIPTIONS } from "../settings.constants"
import type { AiProvider, ProviderInfo } from "../settings.types"
import { ProviderLogo } from "./ProviderLogo"

/** The provider picker: one selectable card per configured provider. */
export function ProviderCardGrid({
  providers,
  selectedProvider,
  onSelect,
}: {
  providers: ProviderInfo[]
  selectedProvider: AiProvider
  onSelect: (providerId: AiProvider) => void
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      {providers.map((provider) => (
        <button
          key={provider.id}
          type="button"
          onClick={() => onSelect(provider.id)}
          className={cn(
            "relative rounded-xl border px-3 py-3 text-left transition-all",
            selectedProvider === provider.id
              ? "border-primary/50 bg-primary/10 ring-1 ring-primary/30"
              : "border-border/40 bg-background/40 hover:bg-accent/40"
          )}
        >
          <div className="mb-2 flex items-center gap-2">
            <ProviderLogo providerId={provider.id} name={provider.name} />
            <span className="text-sm font-semibold text-foreground">{provider.name}</span>
          </div>
          <p className="text-[10px] leading-tight text-muted-foreground line-clamp-2">
            {PROVIDER_DESCRIPTIONS[provider.id]}
          </p>
          {provider.configured_via_env && (
            <span className="absolute -top-1.5 -right-1.5 rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-medium text-emerald-400 ring-1 ring-emerald-500/30">
              ENV
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
