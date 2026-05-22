"use client"

import { useEffect, useState, type Dispatch, type SetStateAction } from "react"

export type SessionMessage = {
  role: string
  content: string
}

function isSessionMessage(value: unknown): value is SessionMessage {
  if (!value || typeof value !== "object") return false
  const maybe = value as Record<string, unknown>
  return typeof maybe.role === "string" && typeof maybe.content === "string"
}

export function loadSessionMessages<T extends SessionMessage>(
  key: string,
  fallback: T[],
): T[] {
  if (typeof window === "undefined") return fallback

  try {
    const raw = window.sessionStorage.getItem(key)
    if (!raw) return fallback
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || !parsed.every(isSessionMessage)) {
      return fallback
    }
    return parsed as T[]
  } catch {
    return fallback
  }
}

export function saveSessionMessages<T extends SessionMessage>(key: string, messages: T[]) {
  if (typeof window === "undefined") return

  try {
    window.sessionStorage.setItem(key, JSON.stringify(messages))
  } catch {
    // Session memory is best-effort only.
  }
}

export function useSessionMessages<T extends SessionMessage>(
  key: string,
  fallback: T[],
): [T[], Dispatch<SetStateAction<T[]>>] {
  const [messages, setMessages] = useState<T[]>(() => loadSessionMessages(key, fallback))

  useEffect(() => {
    saveSessionMessages(key, messages)
  }, [key, messages])

  return [messages, setMessages]
}
