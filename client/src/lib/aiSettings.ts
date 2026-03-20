export type AiModelPreset = "70b" | "8b"

export interface AiSettings {
  enabled: boolean
  modelPreset: AiModelPreset
}

const AI_ENABLED_KEY = "numa_ai_enabled"
const AI_MODEL_PRESET_KEY = "numa_ai_model_preset"

const DEFAULT_AI_SETTINGS: AiSettings = {
  enabled: true,
  modelPreset: "70b",
}

function normalizeModelPreset(value: string | null): AiModelPreset {
  return value === "8b" ? "8b" : "70b"
}

export function getAiSettings(): AiSettings {
  if (typeof window === "undefined") {
    return DEFAULT_AI_SETTINGS
  }

  const enabledRaw = localStorage.getItem(AI_ENABLED_KEY)
  const modelRaw = localStorage.getItem(AI_MODEL_PRESET_KEY)

  const enabled = enabledRaw === null ? DEFAULT_AI_SETTINGS.enabled : enabledRaw === "true"
  const modelPreset = normalizeModelPreset(modelRaw)

  return { enabled, modelPreset }
}

export function setAiSettings(next: Partial<AiSettings>): AiSettings {
  const current = getAiSettings()
  const merged: AiSettings = {
    enabled: typeof next.enabled === "boolean" ? next.enabled : current.enabled,
    modelPreset: next.modelPreset ? normalizeModelPreset(next.modelPreset) : current.modelPreset,
  }

  if (typeof window !== "undefined") {
    localStorage.setItem(AI_ENABLED_KEY, String(merged.enabled))
    localStorage.setItem(AI_MODEL_PRESET_KEY, merged.modelPreset)
  }

  return merged
}
