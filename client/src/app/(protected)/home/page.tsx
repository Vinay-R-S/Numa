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
    <div className="mx-auto flex h-full w-full max-w-6xl flex-col gap-5 px-6 py-6">
      <header className="flex items-center justify-between gap-4 rounded-2xl border border-border/40 bg-card/40 p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
            <BrainCircuit className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Master Agent Console</h1>
            <p className="text-sm text-muted-foreground">
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

      <section className="flex min-h-112 flex-col rounded-2xl border border-border/40 bg-card/40 p-5">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="text-sm text-muted-foreground">
            Ask things like: <span className="text-foreground">"Schedule product sync tomorrow at 10 AM"</span>
          </div>
          {lastDelegation && (
            <span className="rounded-full border border-border/40 bg-background/40 px-3 py-1 text-xs text-muted-foreground">
              Routed to: {lastDelegation}
            </span>
          )}
        </div>

        <div className="mb-3 flex-1 space-y-2 overflow-y-auto rounded-xl border border-border/30 bg-background/40 p-3">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "ml-auto w-fit max-w-[85%] rounded-lg bg-primary/15 px-3 py-2 text-sm text-foreground"
                  : "mr-auto w-fit max-w-[85%] rounded-lg bg-muted/60 px-3 py-2 text-sm text-foreground"
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
            placeholder="Tell Master Agent what to do across your apps"
            className="flex-1 rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
            disabled={sending}
          />
          <Button type="button" onClick={() => void handleSend()} disabled={!canSend}>
            <Send className="mr-1 h-4 w-4" />
            {sending ? "Running..." : "Send"}
          </Button>
        </div>
      </section>
    </div>
  )
}
