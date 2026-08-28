import { LiveDataPill } from "@/components/ui/live-data-pill"

/** Page title bar. The pill tracks the AI settings load, as it did inline. */
export function SettingsPageHeader({ loading }: { loading: boolean }) {
  return (
    <header className="flex flex-col gap-3 rounded-xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:rounded-2xl sm:p-5">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">Settings</h1>
        <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
          Configure AI providers, model selection, and integrations.
        </p>
      </div>
      <LiveDataPill live={!loading} loading={loading} />
    </header>
  )
}
