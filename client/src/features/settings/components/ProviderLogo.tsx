import { PROVIDER_LOGOS } from "../settings.constants"

/** Provider avatar, falling back to an "AI" chip for an unknown provider id. */
export function ProviderLogo({ providerId, name }: { providerId: string; name: string }) {
  const fileName = PROVIDER_LOGOS[providerId]
  if (!fileName) {
    return (
      <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border/50 bg-muted/40 text-[10px] font-bold text-muted-foreground">
        AI
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`/llm-providers/${fileName}`}
      alt={`${name} logo`}
      className="h-8 w-8 rounded-full border border-border/50 bg-background object-cover shadow-sm"
      loading="lazy"
    />
  )
}
