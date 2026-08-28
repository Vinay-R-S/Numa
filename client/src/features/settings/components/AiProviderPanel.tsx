"use client"

import { Key, Loader2, RotateCcw, Save } from "lucide-react"

import { Button } from "@/components/ui/button"

import type { UseAiSettingsReturn } from "../useAiSettings"
import { AlertMessage } from "./AlertMessage"
import { ApiKeyField, OllamaUrlField } from "./ApiKeyField"
import { ModelSelect } from "./ModelSelect"
import { ProviderCardGrid } from "./ProviderCardGrid"
import { SettingsSection } from "./SettingsSection"
import { TemperatureSlider } from "./TemperatureSlider"

export function AiProviderPanel({ ai }: { ai: UseAiSettingsReturn }) {
  const isOllama = ai.selectedProvider === "ollama"
  const hasSavedKey = Boolean(
    ai.currentSettings?.has_api_key && ai.currentSettings.provider === ai.selectedProvider
  )

  return (
    <SettingsSection
      icon={Key}
      title="AI Provider"
      description="Choose your LLM provider and model. API keys are encrypted before storage."
    >
      {ai.loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          <ProviderCardGrid
            providers={ai.providers}
            selectedProvider={ai.selectedProvider}
            onSelect={ai.selectProvider}
          />

          <div className="rounded-xl border border-border/40 bg-background/40 p-3 sm:p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <ModelSelect
                selectedModel={ai.selectedModel}
                options={ai.modelOptions}
                open={ai.modelOpen}
                canOpen={Boolean(ai.selectedProviderInfo)}
                ollamaEmpty={isOllama && ai.ollamaModels.length === 0 && !ai.ollamaLoading}
                ollamaLoading={isOllama && ai.ollamaLoading}
                onToggle={() => ai.setModelOpen(!ai.modelOpen)}
                onSelect={ai.selectModel}
              />

              {isOllama ? (
                <OllamaUrlField value={ai.ollamaUrl} onChange={ai.setOllamaUrl} />
              ) : (
                <ApiKeyField
                  value={ai.apiKey}
                  revealed={ai.showApiKey}
                  hasSavedKey={hasSavedKey}
                  envFallback={Boolean(ai.selectedProviderInfo?.configured_via_env)}
                  onChange={ai.setApiKey}
                  onToggleReveal={() => ai.setShowApiKey(!ai.showApiKey)}
                />
              )}
            </div>

            <TemperatureSlider value={ai.temperature} onChange={ai.setTemperature} />

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="sm"
                className="gap-1.5"
                onClick={() => { void ai.save() }}
                disabled={ai.saving}
              >
                {ai.saving ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5" />
                )}
                Save Settings
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => { void ai.reset() }}
                disabled={ai.saving}
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset to Defaults
              </Button>
            </div>

            {ai.error && <AlertMessage tone="error" className="mt-3">{ai.error}</AlertMessage>}
            {ai.success && (
              <AlertMessage tone="success" className="mt-3">{ai.success}</AlertMessage>
            )}
          </div>
        </div>
      )}
    </SettingsSection>
  )
}
