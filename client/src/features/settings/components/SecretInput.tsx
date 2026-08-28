import { Eye, EyeOff } from "lucide-react"

/**
 * Text input with an optional reveal toggle. The AI panel's API key field and
 * every integration key field rendered this exact markup separately.
 */
export function SecretInput({
  value,
  placeholder,
  secret = true,
  revealed = false,
  onChange,
  onToggleReveal,
}: {
  value: string
  placeholder: string
  secret?: boolean
  revealed?: boolean
  onChange: (value: string) => void
  onToggleReveal?: () => void
}) {
  return (
    <div className="relative">
      <input
        type={secret && !revealed ? "password" : "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-border/60 bg-background/60 px-3 py-2 pr-9 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
      />
      {secret && onToggleReveal && (
        <button
          type="button"
          onClick={onToggleReveal}
          className="absolute top-1/2 right-2.5 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          {revealed ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
        </button>
      )}
    </div>
  )
}
