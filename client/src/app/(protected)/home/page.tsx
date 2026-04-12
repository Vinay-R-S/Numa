"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { Bot, BrainCircuit, Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  MasterAgentMessage,
  sendMasterAgentCommand,
} from "@/components/agents/masterAgentApi"

interface User {
  id: string
  email: string
  full_name?: string
}

export default function HomePage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [messages, setMessages] = useState<MasterAgentMessage[]>([
    {
      role: "assistant",
      content:
        "I am your Master Agent. I can call the Calendar sub-agent and Task sub-agent to perform actions for you.",
    },
  ])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastDelegation, setLastDelegation] = useState<string | null>(null)
  const [refreshHint, setRefreshHint] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem("numa_token")
    if (!token) return

    fetch(`/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.status === 401) {
          localStorage.removeItem("numa_token")
          router.replace("/auth")
          return null
        }
        return res.json()
      })
      .then((data) => {
        if (data) setUser(data)
      })
  }, [router])

  const canSend = useMemo(() => input.trim().length > 0 && !sending, [input, sending])

  async function handleSend() {
    const query = input.trim()
    if (!query || sending) {
      return
    }

    const nextHistory: MasterAgentMessage[] = [...messages, { role: "user", content: query }]
    setMessages(nextHistory)
    setInput("")
    setSending(true)
    setError(null)
    setRefreshHint(null)

    try {
      const result = await sendMasterAgentCommand(query, nextHistory)
      setMessages((prev) => [...prev, { role: "assistant", content: result.response }])

      if (result.delegated_to) {
        setLastDelegation(result.delegated_to)
      }

      if (result.refreshCalendar || result.refreshTasks) {
        const hints = []
        if (result.refreshCalendar) hints.push("Calendar")
        if (result.refreshTasks) hints.push("Task List")
        setRefreshHint(`Updated: ${hints.join(" + ")}`)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Master agent request failed"
      setError(message)
      setMessages((prev) => [...prev, { role: "assistant", content: `I hit an error: ${message}` }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mx-auto flex h-full w-full max-w-6xl flex-col gap-4 px-3 py-4 sm:gap-5 sm:px-6 sm:py-6">
      <header className="flex flex-col gap-3 rounded-xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:rounded-2xl sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20 sm:h-11 sm:w-11">
            <BrainCircuit className="h-5 w-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-xl font-bold tracking-tight text-foreground sm:text-2xl">Master Agent Console</h1>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Orchestrates sub-agents across Calendar and Task List using Groq.
            </p>
          </div>
        </div>

        {user && (
          <div className="rounded-lg border border-border/30 bg-background/40 px-3 py-2 text-xs text-muted-foreground">
            Signed in as <span className="font-medium text-foreground">{user.full_name || user.email}</span>
          </div>
        )}
      </header>

      <section className="flex min-h-0 flex-1 flex-col rounded-xl border border-border/40 bg-card/40 p-3 sm:min-h-112 sm:rounded-2xl sm:p-5">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-xs text-muted-foreground sm:text-sm">
            Ask things like: <span className="text-foreground">"Schedule product sync tomorrow at 10 AM"</span>
          </div>
          {lastDelegation && (
            <span className="w-fit rounded-full border border-border/40 bg-background/40 px-3 py-1 text-xs text-muted-foreground">
              Routed to: {lastDelegation}
            </span>
          )}
        </div>

        <div className="relative mb-3 min-h-0 flex-1 space-y-2 overflow-y-auto rounded-xl border border-border/30 bg-background/40 p-2 sm:p-3">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "ml-auto w-fit max-w-[90%] rounded-lg bg-primary/15 px-3 py-2 text-sm text-foreground sm:max-w-[85%]"
                  : "mr-auto w-fit max-w-[90%] rounded-lg bg-muted/60 px-3 py-2 text-sm text-foreground sm:max-w-[85%]"
              }
            >
              {message.role === "assistant" && <Bot className="mr-1 inline h-3.5 w-3.5 text-primary" />}
              {message.content}
            </div>
          ))}
        </div>

        {refreshHint && <p className="mb-2 text-sm text-emerald-500">{refreshHint}</p>}
        {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

        <div className="flex gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                void handleSend()
              }
            }}
            placeholder="Tell Master Agent what to do..."
            className="flex-1 rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
            disabled={sending}
          />
          <Button type="button" size="sm" className="shrink-0 sm:size-default" onClick={() => void handleSend()} disabled={!canSend}>
            <Send className="h-4 w-4 sm:mr-1" />
            <span className="hidden sm:inline">{sending ? "Running..." : "Send"}</span>
          </Button>
        </div>
      </section>
    </div>
  )
}
