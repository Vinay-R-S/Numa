"use client"

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Activity,
  Bot,
  Flame,
  Footprints,
  Heart,
  MapPin,
  Moon,
  RefreshCw,
  Send,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wifi,
  WifiOff,
  X,
  Zap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  HealthAgentMessage,
  HealthSnapshot,
  HealthStatus,
  getHealthSnapshots,
  getHealthStatus,
  sendHealthAgentCommand,
  syncAllHealth,
} from "@/components/health/healthApi"

// ── Helpers ─────────────────────────────────────────────────────────────────────

function formatNumber(n: number | null | undefined): string {
  if (n == null) return "-"
  return n >= 1000 ? n.toLocaleString() : String(Math.round(n * 10) / 10)
}

function pct(value: number | null, goal: number): number {
  if (!value) return 0
  return Math.min(100, Math.round((value / goal) * 100))
}

// ── Metric Card ─────────────────────────────────────────────────────────────────

function MetricCard({
  icon: Icon,
  label,
  value,
  unit,
  goal,
  color,
}: {
  icon: React.ElementType
  label: string
  value: number | null
  unit: string
  goal: number
  color: string
}) {
  const percentage = pct(value, goal)
  const remaining = goal - (value || 0)
  const goalMet = (value || 0) >= goal

  return (
    <div className="group relative rounded-2xl border border-border/40 bg-card/40 p-3 transition-all hover:-translate-y-1 hover:border-border/60 sm:p-5">
      <div className="flex items-center gap-2.5 mb-4">
        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-muted-foreground truncate">{label}</p>
          <p className="text-[10px] text-muted-foreground/60 leading-none mt-0.5">
            Goal: {goal >= 1000 ? goal.toLocaleString() : goal} {unit}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Circular progress */}
        <div className="relative shrink-0">
          <svg width={64} height={64} viewBox="0 0 80 80" className="sm:h-[80px] sm:w-[80px]" style={{ transform: "rotate(-90deg)" }}>
            <circle cx={40} cy={40} r={34} fill="none" stroke="currentColor" strokeWidth={6}
              className="text-border/20" />
            <circle cx={40} cy={40} r={34} fill="none" stroke="currentColor" strokeWidth={6}
              className={color.replace("bg-", "text-").replace("/80", "")}
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 34}
              strokeDashoffset={2 * Math.PI * 34 * (1 - percentage / 100)}
              style={{ transition: "stroke-dashoffset 1s ease-out" }} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-sm font-bold text-foreground tabular-nums">{percentage}</span>
            <span className="text-[9px] text-muted-foreground">%</span>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-1 mb-1">
            <span className="text-xl font-black text-foreground tabular-nums leading-none sm:text-2xl">
              {formatNumber(value)}
            </span>
            <span className="text-sm text-muted-foreground font-medium">{unit}</span>
          </div>
          <p className={`text-[10px] font-semibold ${goalMet ? "text-emerald-400" : "text-muted-foreground"}`}>
            {goalMet ? "Goal reached!" : `${formatNumber(remaining > 0 ? remaining : 0)} ${unit} to go`}
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Weekly chart bar ────────────────────────────────────────────────────────────

function WeeklyBar({ snapshots }: { snapshots: HealthSnapshot[] }) {
  const gfitDays = snapshots
    .filter((s) => s.source === "google_fit")
    .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))

  if (gfitDays.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-muted-foreground">No weekly data yet. Sync Google Fit to see trends.</p>
      </div>
    )
  }

  const maxSteps = Math.max(...gfitDays.map((d) => d.steps || 0), 1)
  const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
  const today = new Date().toISOString().slice(0, 10)

  return (
    <div className="flex items-end gap-2 h-40 px-2">
      {gfitDays.map((day) => {
        const steps = day.steps || 0
        const height = Math.max((steps / maxSteps) * 100, 4)
        const d = new Date(day.snapshot_date)
        const label = DAY_NAMES[d.getUTCDay()]
        const isToday = day.snapshot_date === today

        return (
          <div key={day.snapshot_date} className="flex flex-1 flex-col items-center gap-1">
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {steps >= 1000 ? `${(steps / 1000).toFixed(1)}k` : steps}
            </span>
            <div
              className={`w-full rounded-t-lg transition-all ${isToday ? "bg-primary/80" : "bg-primary/30"}`}
              style={{ height: `${height}%` }}
            />
            <span className={`text-[10px] font-medium ${isToday ? "text-foreground" : "text-muted-foreground/60"}`}>
              {label}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// ── Sleep card ───────────────────────────────────────────────────────────────────

function SleepCard({ snapshot }: { snapshot: HealthSnapshot | null }) {
  const sleep = snapshot?.sleep_hours
  const stages = snapshot?.sleep_stages

  if (!sleep || sleep <= 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border/40 bg-card/40 p-6 min-h-[200px]">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/10">
          <Moon className="h-6 w-6 text-indigo-400/50" />
        </div>
        <p className="text-sm font-medium text-muted-foreground">No sleep data</p>
        <p className="text-xs text-muted-foreground/60 text-center max-w-[200px]">
          Sleep tracking must be enabled in Google Fit or a connected wearable.
        </p>
      </div>
    )
  }

  const goal = 8
  const quality = Math.min(100, Math.round((sleep / goal) * 100))
  const stageList = stages
    ? [
        { name: "Deep", hours: stages.deep || 0, cls: "bg-indigo-500" },
        { name: "Light", hours: stages.light || 0, cls: "bg-blue-500" },
        { name: "REM", hours: stages.rem || 0, cls: "bg-purple-500" },
      ].filter((s) => s.hours > 0)
    : []

  return (
    <div className="rounded-2xl border border-border/40 bg-card/40 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 ring-1 ring-indigo-500/20">
            <Moon className="h-5 w-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">Sleep Analysis</h3>
            <p className="text-xs text-muted-foreground">Last night</p>
          </div>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${
          quality >= 80 ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
          : quality >= 60 ? "border-yellow-500/20 bg-yellow-500/10 text-yellow-400"
          : "border-orange-500/20 bg-orange-500/10 text-orange-400"
        }`}>
          {quality}%
        </span>
      </div>

      <div className="flex items-baseline gap-1 mb-3">
        <span className="text-4xl font-black text-indigo-400 tabular-nums">{Math.floor(sleep)}</span>
        <span className="text-lg text-muted-foreground">h</span>
        <span className="text-3xl font-black text-indigo-400 tabular-nums">{Math.round((sleep % 1) * 60)}</span>
        <span className="text-base text-muted-foreground">m</span>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <div className="flex-1 h-2 rounded-full bg-border/20 overflow-hidden">
          <div
            className="h-full bg-linear-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
            style={{ width: `${Math.min(100, (sleep / goal) * 100)}%` }}
          />
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap">{goal}h goal</span>
      </div>

      {stageList.length > 0 && (
        <>
          <div className="h-5 rounded-lg overflow-hidden flex mb-3">
            {stageList.map((s) => (
              <div key={s.name} className={`h-full ${s.cls}`} style={{ width: `${(s.hours / sleep) * 100}%` }} title={`${s.name}: ${s.hours}h`} />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2">
            {stageList.map((s) => (
              <div key={s.name} className="rounded-lg border border-border/30 bg-background/40 p-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <div className={`h-2 w-2 rounded-full ${s.cls}`} />
                  <span className="text-[10px] text-muted-foreground">{s.name}</span>
                </div>
                <p className="text-sm font-bold text-foreground">{s.hours.toFixed(1)}h</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ── Health Score ─────────────────────────────────────────────────────────────────

function HealthScore({ snapshot }: { snapshot: HealthSnapshot | null }) {
  const steps = snapshot?.steps || 0
  const active = snapshot?.active_minutes || 0
  const cal = snapshot?.calories || 0
  const sleep = snapshot?.sleep_hours || 0

  const score = Math.round(
    Math.min(steps / 10000, 1) * 25 +
    Math.min(active / 60, 1) * 25 +
    Math.min(cal / 2500, 1) * 25 +
    Math.min(sleep / 8, 1) * 25
  )

  const level = score >= 75 ? "Excellent" : score >= 50 ? "Good" : score >= 25 ? "Fair" : "Needs Work"
  const color = score >= 75 ? "text-emerald-400" : score >= 50 ? "text-yellow-400" : score >= 25 ? "text-orange-400" : "text-red-400"
  const ringColor = score >= 75 ? "text-emerald-500" : score >= 50 ? "text-yellow-500" : score >= 25 ? "text-orange-500" : "text-red-500"

  return (
    <div className="rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-6">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-5">
        {/* Score ring */}
        <div className="relative shrink-0">
          <svg width={80} height={80} viewBox="0 0 100 100" className="sm:h-[100px] sm:w-[100px]" style={{ transform: "rotate(-90deg)" }}>
            <circle cx={50} cy={50} r={42} fill="none" stroke="currentColor" strokeWidth={8} className="text-border/20" />
            <circle cx={50} cy={50} r={42} fill="none" stroke="currentColor" strokeWidth={8}
              className={ringColor} strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 42}
              strokeDashoffset={2 * Math.PI * 42 * (1 - score / 100)}
              style={{ transition: "stroke-dashoffset 1.2s ease-out" }} />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-black tabular-nums ${color}`}>{score}</span>
            <span className="text-[9px] text-muted-foreground">Health</span>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20">
              <Heart className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-extrabold text-foreground leading-none">Your Daily Health</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Based on today&apos;s activity</p>
            </div>
          </div>
          <div className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${
            score >= 75 ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
            : score >= 50 ? "border-yellow-500/20 bg-yellow-500/10 text-yellow-400"
            : "border-orange-500/20 bg-orange-500/10 text-orange-400"
          }`}>
            {level}
          </div>

          <div className="mt-3 w-full h-2 bg-border/20 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all bg-linear-to-r ${
                score >= 75 ? "from-emerald-500 to-green-400"
                : score >= 50 ? "from-yellow-500 to-amber-400"
                : "from-orange-500 to-red-400"
              }`}
              style={{ width: `${score}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Chat Bubble ─────────────────────────────────────────────────────────────────

function ChatBubble({ msg }: { msg: HealthAgentMessage }) {
  const isUser = msg.role === "user"
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <Bot className="h-3.5 w-3.5 text-primary" />
        </div>
      )}
      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-line ${
        isUser ? "bg-primary/15 text-foreground rounded-br-sm" : "bg-muted/50 text-foreground rounded-bl-sm"
      }`}>
        {msg.content}
      </div>
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────────────────────────

export default function HealthPage() {
  const [status, setStatus] = useState<HealthStatus | null>(null)
  const [snapshots, setSnapshots] = useState<HealthSnapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Agent panel
  const [agentOpen, setAgentOpen] = useState(false)
  const [chatMessages, setChatMessages] = useState<HealthAgentMessage[]>([
    { role: "assistant", content: "Hi! I'm your NUMA Health agent. I can show your fitness data, weekly trends, and personalized insights from Google Fit and Strava. What would you like to know?" },
  ])
  const [chatInput, setChatInput] = useState("")
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // ── Load data ───────────────────────────────────────────────────────────────

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [s, snaps] = await Promise.all([getHealthStatus(), getHealthSnapshots({ days: 8 })])
      setStatus(s)
      setSnapshots(snaps)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load health data")
    } finally {
      setLoading(false)
    }
  }, [])

  const handleSync = useCallback(async () => {
    setSyncing(true)
    try {
      await syncAllHealth()
      await loadData()
    } catch {
      // ignore sync errors
    } finally {
      setSyncing(false)
    }
  }, [loadData])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  // ── Chat ──────────────────────────────────────────────────────────────────────

  const handleSend = async () => {
    const q = chatInput.trim()
    if (!q || sending) return
    const next: HealthAgentMessage[] = [...chatMessages, { role: "user", content: q }]
    setChatMessages(next)
    setChatInput("")
    setSending(true)
    setChatError(null)
    try {
      const result = await sendHealthAgentCommand(q, next)
      setChatMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.refresh_health) void loadData()
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed"
      setChatError(msg)
      setChatMessages((prev) => [...prev, { role: "assistant", content: `Error: ${msg}` }])
    } finally {
      setSending(false)
    }
  }

  const canSend = useMemo(() => chatInput.trim().length > 0 && !sending, [chatInput, sending])

  // ── Derived data ──────────────────────────────────────────────────────────────

  const todayStr = new Date().toISOString().slice(0, 10)
  const todayGfit = snapshots.find((s) => s.source === "google_fit" && s.snapshot_date === todayStr) || null
  const isLive = snapshots.length > 0

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full w-full flex-col gap-4 overflow-y-auto px-4 py-4 sm:px-6 sm:py-6">

      {/* Header */}
      <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 ring-1 ring-emerald-500/20">
            <Activity className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              Health Dashboard
            </h1>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Google Fit + Strava &bull; 7-day rolling window &bull; Synced to Supabase
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold ${
            isLive
              ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
              : "border-border/30 bg-background/40 text-muted-foreground"
          }`}>
            {isLive ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            {isLive ? "Live Data" : "No Data"}
          </div>
          <Button variant="ghost" size="sm" onClick={() => void handleSync()} className="gap-2 text-muted-foreground hover:text-foreground">
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">{syncing ? "Syncing..." : "Sync"}</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={() => void loadData()} className="gap-2 text-muted-foreground hover:text-foreground">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
          <Button
            variant={agentOpen ? "default" : "outline"}
            size="sm"
            onClick={() => setAgentOpen((v) => !v)}
            className="gap-2"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Agent</span>
          </Button>
        </div>
      </header>

      {error && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Health Score */}
      <HealthScore snapshot={todayGfit} />

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard icon={Footprints} label="Steps" value={todayGfit?.steps ?? null}
          unit="steps" goal={10000} color="bg-cyan-500/80" />
        <MetricCard icon={Activity} label="Active Minutes" value={todayGfit?.active_minutes ?? null}
          unit="min" goal={60} color="bg-emerald-500/80" />
        <MetricCard icon={Flame} label="Calories" value={todayGfit?.calories ?? null}
          unit="kcal" goal={2500} color="bg-orange-500/80" />
        <MetricCard icon={MapPin} label="Distance" value={todayGfit?.distance_km ?? null}
          unit="km" goal={8} color="bg-purple-500/80" />
        <MetricCard icon={Moon} label="Sleep" value={todayGfit?.sleep_hours ?? null}
          unit="hrs" goal={8} color="bg-indigo-500/80" />
      </div>

      {/* Weekly Chart */}
      <section className="rounded-2xl border border-border/40 bg-card/40 p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/10 ring-1 ring-cyan-500/20">
            <TrendingUp className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">Weekly Activity</h3>
            <p className="text-xs text-muted-foreground">Last 7 days - steps per day</p>
          </div>
        </div>
        <WeeklyBar snapshots={snapshots} />
      </section>

      {/* Sleep Analysis */}
      <SleepCard snapshot={todayGfit} />

      {/* Floating Agent Panel */}
      {agentOpen && (
        <section className="fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:bottom-6 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4">

          {/* Chat header */}
          <div className="flex items-center gap-2 border-b border-border/40 px-1 pb-3 shrink-0">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
              <Zap className="h-3.5 w-3.5 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">Health Agent</span>
            <span className="ml-auto rounded-full border border-border/30 bg-background/40 px-2 py-0.5 text-[10px] text-muted-foreground">
              Groq &bull; LangGraph
            </span>
            <button
              onClick={() => setAgentOpen(false)}
              className="ml-1 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Quick actions */}
          <div className="border-b border-border/20 px-1 py-2 shrink-0">
            <div className="flex flex-wrap gap-1.5">
              {["How am I doing today?", "Show weekly trends", "Recommend a diet plan", "Suggest yoga for me", "Give me insights"].map((s) => (
                <button key={s} onClick={() => setChatInput(s)}
                  className="rounded-full border border-border/40 bg-background/40 px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-foreground">
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-3 px-1 py-3 min-h-0">
            {chatMessages.map((msg, i) => (
              <ChatBubble key={`${msg.role}-${i}`} msg={msg} />
            ))}
            {sending && (
              <div className="flex items-start gap-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="rounded-2xl rounded-bl-sm bg-muted/50 px-4 py-3">
                  <div className="flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}
            {chatError && (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">{chatError}</p>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-border/40 px-1 pt-3 shrink-0">
            <div className="flex gap-2">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void handleSend() } }}
                placeholder="Ask the Health agent..."
                disabled={sending}
                className="flex-1 rounded-xl border border-border/40 bg-background px-3.5 py-2 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-50"
              />
              <Button type="button" size="sm" onClick={() => void handleSend()} disabled={!canSend} className="shrink-0">
                <Send className="h-4 w-4 sm:mr-1" />
                <span className="hidden sm:inline">{sending ? "..." : "Send"}</span>
              </Button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
