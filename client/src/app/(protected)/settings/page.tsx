"use client"

import {
  AgentTogglePanel,
  AiProviderPanel,
  GoogleCalendarPanel,
  IntegrationKeysPanel,
  SettingsPageHeader,
  SlackPanel,
  TimelinePanel,
  useAiSettings,
  useCalendarConnection,
  useSlackConnection,
  useTimelineSettings,
} from "@/features/settings"

export default function SettingsPage() {
  const ai = useAiSettings()
  const calendar = useCalendarConnection()
  const slack = useSlackConnection()
  const timeline = useTimelineSettings()

  return (
    <div className="flex min-h-full w-full flex-col gap-4 px-4 py-4 sm:gap-6 sm:px-6 sm:py-6">
      <SettingsPageHeader loading={ai.loading} />

      <AiProviderPanel ai={ai} />

      <GoogleCalendarPanel calendar={calendar} />

      <SlackPanel slack={slack} />

      <AgentTogglePanel
        enabled={ai.aiEnabled}
        currentSettings={ai.currentSettings}
        onToggle={ai.toggleAi}
      />

      <TimelinePanel timeline={timeline} />

      <IntegrationKeysPanel />
    </div>
  )
}
