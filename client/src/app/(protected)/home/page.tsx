"use client"

import React, { useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import {
  Bot, BrainCircuit, Send, RefreshCw, CalendarDays, CheckSquare,
  MessageSquare, Activity, GitBranch, Code2, BookOpen, Loader2,
  ArrowRight, TrendingUp, Footprints, Flame, Moon, Clock, Sparkles, X,
  ListTodo, AlertCircle, Zap, MapPin, Heart,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useDashboardStore } from "@/lib/stores"
import {
  MasterAgentMessage,
  fetchLatestAgentData,
  sendMasterAgentCommand,
} from "@/components/agents/masterAgentApi"

interface User { id: string; email: string; full_name?: string }

const ICON_COLORS = {
  tasks: "text-blue-400",
  completed: "text-emerald-400",
  inprogress: "text-amber-400",
  pending: "text-rose-400",
  streak: "text-orange-400",
  calendar: "text-sky-400",
  slack: "text-purple-400",
  journal: "text-pink-400",
  health: "text-emerald-400",
  steps: "text-cyan-400",
  calories: "text-orange-400",
  sleep: "text-indigo-400",
  distance: "text-violet-400",
  github: "text-violet-400",
  active: "text-emerald-400",
} as const

const StatCard = React.memo(function StatCard({ icon: Icon, label, value, sub, href, iconColor }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; href?: string; color?: string; iconColor?: string
}) {
  const inner = (
    <div className={cn(
      "rounded-xl border border-border/40 bg-card/40 p-4 transition-all",
      href && "hover:bg-accent/30 hover:border-border/60 cursor-pointer"
    )}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <Icon className={cn("h-4 w-4", iconColor || "text-muted-foreground")} />
      </div>
      <p className="text-2xl font-bold text-foreground sm:text-3xl tabular-nums">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
  if (href) return <a href={href} className="block">{inner}</a>
  return inner
})

function HealthRingCard({ icon: Icon, label, value, unit, goal, iconColor, ringColor }: {
  icon: React.ElementType; label: string; value: number; unit: string; goal: number; iconColor: string; ringColor: string
}) {
  const pct = Math.min(value / goal, 1)
  const r = 28
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-border/40 bg-card/40 p-3">
      <div className="relative h-16 w-16">
        <svg viewBox="0 0 64 64" className="h-full w-full -rotate-90">
          <circle cx="32" cy="32" r={r} fill="none" strokeWidth="5" className="stroke-muted/30" />
          <circle
            cx="32" cy="32" r={r} fill="none" strokeWidth="5"
            strokeLinecap="round"
            className={ringColor}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <Icon className={cn("h-4 w-4", iconColor)} />
        </div>
      </div>
      <div className="text-center">
        <div className="flex items-baseline justify-center gap-0.5">
          <span className="text-sm font-bold text-foreground tabular-nums">{typeof value === "number" && value % 1 !== 0 ? value.toFixed(1) : value.toLocaleString()}</span>
          <span className="text-[10px] text-muted-foreground">{unit}</span>
        </div>
        <p className="text-[10px] text-muted-foreground">{label}</p>
        <p className="text-[9px] text-muted-foreground/60">{Math.round(pct * 100)}% of {goal.toLocaleString()}</p>
      </div>
    </div>
  )
}

function TaskDistributionChart({ completed, inprogress, pending }: { completed: number; inprogress: number; pending: number }) {
  const total = completed + inprogress + pending
  if (total === 0) return null
  const items = [
    { label: "Completed", value: completed, color: "fill-emerald-400" },
    { label: "In Progress", value: inprogress, color: "fill-amber-400" },
    { label: "Pending", value: pending, color: "fill-rose-400" },
  ]
  const maxVal = Math.max(...items.map((d) => d.value), 1)
  const barW = 40
  const gap = 24
  const chartW = items.length * barW + (items.length - 1) * gap
  const chartH = 80
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Zap className={cn("h-4 w-4", ICON_COLORS.tasks)} />
        <span className="text-sm font-semibold text-foreground">Task Distribution</span>
      </div>
      <div className="flex items-end justify-center">
        <svg width={chartW} height={chartH + 20} viewBox={`0 0 ${chartW} ${chartH + 20}`}>
          {items.map((item, i) => {
            const barH = Math.max((item.value / maxVal) * chartH, 4)
            const x = i * (barW + gap)
            return (
              <g key={item.label}>
                <rect x={x} y={chartH - barH} width={barW} height={barH} rx={4} className={item.color} opacity={0.85} />
                <text x={x + barW / 2} y={chartH - barH - 4} textAnchor="middle" className="fill-foreground text-[10px] font-medium">{item.value}</text>
                <text x={x + barW / 2} y={chartH + 14} textAnchor="middle" className="fill-muted-foreground text-[9px]">{item.label}</text>
              </g>
            )
          })}
        </svg>
      </div>
      <div className="mt-3 flex items-center justify-center gap-4">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div className={cn("h-2 w-2 rounded-full", item.color.replace("fill-", "bg-"))} />
            <span className="text-[10px] text-muted-foreground">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function WeeklyActivitySparkline({ todaySteps }: { todaySteps: number }) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
  const todayIdx = new Date().getDay()
  const adjustedIdx = todayIdx === 0 ? 6 : todayIdx - 1
  const data = days.map((d, i) => ({
    label: d,
    value: i === adjustedIdx ? todaySteps : 0,
    isToday: i === adjustedIdx,
  }))
  const maxVal = Math.max(...data.map((d) => d.value), 1)
  const barW = 24
  const gap = 8
  const chartW = data.length * barW + (data.length - 1) * gap
  const chartH = 48
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Activity className={cn("h-4 w-4", ICON_COLORS.active)} />
        <span className="text-sm font-semibold text-foreground">Weekly Activity</span>
        <span className="ml-auto text-[10px] text-muted-foreground">Steps</span>
      </div>
      <div className="flex items-end justify-center">
        <svg width={chartW} height={chartH + 18} viewBox={`0 0 ${chartW} ${chartH + 18}`}>
          {data.map((d, i) => {
            const barH = d.value > 0 ? Math.max((d.value / maxVal) * chartH, 4) : 6
            const x = i * (barW + gap)
            return (
              <g key={d.label}>
                <rect
                  x={x} y={chartH - barH} width={barW} height={barH} rx={3}
                  className={d.isToday ? "fill-cyan-400" : "fill-muted/40"}
                  opacity={d.isToday ? 0.9 : 0.5}
                />
                <text x={x + barW / 2} y={chartH + 14} textAnchor="middle" className={cn("text-[9px]", d.isToday ? "fill-foreground font-medium" : "fill-muted-foreground")}>{d.label}</text>
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}

function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-border/40 bg-card/40 p-4 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="h-3 w-16 rounded bg-muted/50" />
        <div className="h-4 w-4 rounded bg-muted/50" />
      </div>
      <div className="h-8 w-12 rounded bg-muted/50" />
      <div className="mt-1 h-3 w-20 rounded bg-muted/30" />
    </div>
  )
}

export default function HomePage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const { stats, statsLoading, fetchStats: loadStats } = useDashboardStore()
  const [agentOpen, setAgentOpen] = useState(false)

  const [messages, setMessages] = useState<MasterAgentMessage[]>([
    { role: "assistant", content: "I'm your Master Agent. I can manage Calendar, Tasks, Slack, Health, GitHub, LeetCode, and Journal for you. What would you like to do?" },
  ])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [lastDelegation, setLastDelegation] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const canSend = useMemo(() => input.trim().length > 0 && !sending, [input, sending])

  useEffect(() => {
    const token = localStorage.getItem("numa_token")
    if (!token) return
    fetch(`/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => { if (res.status === 401) { localStorage.removeItem("numa_token"); router.replace("/auth"); return null }; return res.json() })
      .then((data) => { if (data) setUser(data) })
  }, [router])

  useEffect(() => { loadStats() }, [loadStats])
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  async function handleSend() {
    const query = input.trim()
    if (!query || sending) return
    const nextHistory: MasterAgentMessage[] = [...messages, { role: "user", content: query }]
    setMessages(nextHistory)
    setInput("")
    setSending(true)
    setChatError(null)
    try {
      const result = await sendMasterAgentCommand(query, nextHistory)
      setMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.delegated_to) setLastDelegation(result.delegated_to)
      if (result.refreshCalendar || result.refreshTasks || result.refreshHealth || result.refreshGithub || result.refreshJournal) {
        loadStats(true)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed"
      setChatError(msg)
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${msg}` }])
    } finally { setSending(false) }
  }

  async function handleFetchLatest() {
    try {
      await fetchLatestAgentData()
      loadStats(true)
    } catch { /* silent */ }
  }

  const h = stats?.health || {}
  const t = stats?.tasks || { total: 0, completed: 0, inprogress: 0, pending: 0, streak: 0, recent: [] }

  const upcomingEvents = useMemo(() => {
    if (!stats?.calendar?.upcoming) return []
    const now = new Date()
    return stats.calendar.upcoming.filter(ev => new Date(ev.start_at) >= now)
  }, [stats?.calendar?.upcoming])

  return (
    <div className="h-full w-full overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
      <div className="space-y-5">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              {user ? `Welcome, ${user.full_name || user.email.split("@")[0]}` : "Dashboard"}
            </h1>
            <p className="text-xs text-muted-foreground sm:text-sm">Your NUMA overview for today</p>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" size="sm" variant="outline" className="gap-1.5" onClick={() => { handleFetchLatest() }}>
              <RefreshCw className="h-3.5 w-3.5" /> Sync All
            </Button>
            <Button
              type="button" size="sm"
              variant={agentOpen ? "default" : "outline"}
              className="gap-1.5"
              onClick={() => setAgentOpen((o) => !o)}
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Agent</span>
            </Button>
          </div>
        </div>

        {statsLoading && !stats ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {[...Array(5)].map((_, i) => <StatCardSkeleton key={i} />)}
            </div>
          </div>
        ) : stats ? (
          <>
            {/* Task Stats Row */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              <StatCard icon={ListTodo} label="Total Tasks" value={t.total} sub="all time" href="/tasklist" iconColor={ICON_COLORS.tasks} />
              <StatCard icon={CheckSquare} label="Completed" value={t.completed} sub="done" href="/tasklist" iconColor={ICON_COLORS.completed} />
              <StatCard icon={TrendingUp} label="In Progress" value={t.inprogress ?? 0} sub="active" href="/tasklist" iconColor={ICON_COLORS.inprogress} />
              <StatCard icon={AlertCircle} label="Pending" value={t.pending} sub="blocked" href="/tasklist" iconColor={ICON_COLORS.pending} />
              <StatCard icon={Flame} label="Current Streak" value={`${t.streak ?? 0}d`} sub="consecutive days" iconColor={ICON_COLORS.streak} />
            </div>

            {/* Task Distribution Chart */}
            <TaskDistributionChart completed={t.completed} inprogress={t.inprogress ?? 0} pending={t.pending} />

            {/* Calendar + Slack + Journal Row */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <StatCard icon={CalendarDays} label="Events Today" value={stats.calendar.today_events} sub={`${upcomingEvents.length} upcoming`} href="/calendar" iconColor={ICON_COLORS.calendar} />
              <StatCard icon={MessageSquare} label="Slack Messages" value={stats.slack.messages_7d} sub={`${stats.slack.active_channels} channels (7d)`} href="/slack" iconColor={ICON_COLORS.slack} />
              <StatCard icon={BookOpen} label="Journal Streak" value={`${stats.journal.streak}d`} sub={stats.journal.today_mood ? `Today: ${stats.journal.today_mood}` : "No entry yet"} href="/journal" iconColor={ICON_COLORS.journal} />
            </div>

            {/* Health Section */}
            <div className="rounded-xl border border-border/40 bg-card/40 p-4 sm:p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Heart className={cn("h-4 w-4", ICON_COLORS.health)} />
                  <span className="text-sm font-semibold text-foreground">Today&apos;s Health</span>
                </div>
                <a href="/health" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
                  Details <ArrowRight className="h-3 w-3" />
                </a>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                <HealthRingCard icon={Footprints} label="Steps" value={h.steps ?? 0} unit="steps" goal={10000} iconColor={ICON_COLORS.steps} ringColor="stroke-cyan-400" />
                <HealthRingCard icon={Activity} label="Active Minutes" value={h.active_minutes ?? 0} unit="min" goal={60} iconColor={ICON_COLORS.active} ringColor="stroke-emerald-400" />
                <HealthRingCard icon={Flame} label="Calories" value={h.calories ?? 0} unit="kcal" goal={2000} iconColor={ICON_COLORS.calories} ringColor="stroke-orange-400" />
                <HealthRingCard icon={Moon} label="Sleep" value={h.sleep_hours ?? 0} unit="hrs" goal={8} iconColor={ICON_COLORS.sleep} ringColor="stroke-indigo-400" />
                <HealthRingCard icon={MapPin} label="Distance" value={h.distance_km ?? 0} unit="km" goal={5} iconColor={ICON_COLORS.distance} ringColor="stroke-violet-400" />
              </div>
            </div>

            {/* Weekly Activity Sparkline */}
            <WeeklyActivitySparkline todaySteps={h.steps ?? 0} />

            {/* Two Column: Upcoming Events + Dev */}
            <div className="grid gap-3 sm:grid-cols-2">
              {/* Upcoming Events */}
              <div className="rounded-xl border border-border/40 bg-card/40 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CalendarDays className={cn("h-4 w-4", ICON_COLORS.calendar)} />
                    <span className="text-sm font-semibold text-foreground">Upcoming Events</span>
                  </div>
                  <a href="/calendar" className="text-xs text-muted-foreground hover:text-foreground">View all</a>
                </div>
                {upcomingEvents.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">No upcoming events</p>
                ) : (
                  <div className="space-y-2">
                    {upcomingEvents.slice(0, 5).map((ev, i) => (
                      <div key={i} className="flex items-center gap-3 rounded-lg bg-background/40 px-3 py-2">
                        <Clock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium text-foreground">{ev.title}</p>
                          <p className="text-[10px] text-muted-foreground">
                            {new Date(ev.start_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Dev Section */}
              <div className="rounded-xl border border-border/40 bg-card/40 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Code2 className={cn("h-4 w-4", ICON_COLORS.github)} />
                    <span className="text-sm font-semibold text-foreground">Developer</span>
                  </div>
                  <a href="/productivity" className="text-xs text-muted-foreground hover:text-foreground">View all</a>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-3 rounded-lg bg-background/40 px-3 py-2">
                    <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs text-foreground">
                      GitHub: {stats.github.connected
                        ? <span className="text-emerald-400 font-medium">@{stats.github.username}</span>
                        : <span className="text-muted-foreground">Not connected</span>}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Tasks */}
            <div className="rounded-xl border border-border/40 bg-card/40 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckSquare className="h-4 w-4 text-amber-400" />
                  <span className="text-sm font-semibold text-foreground">Recent Tasks</span>
                </div>
                <a href="/tasklist" className="text-xs text-muted-foreground hover:text-foreground">View all</a>
              </div>
              {t.recent.length === 0 ? (
                <p className="text-xs text-muted-foreground py-4 text-center">No tasks yet</p>
              ) : (
                <div className="space-y-1.5">
                  {t.recent.map((task, i) => (
                    <div key={i} className="flex items-center gap-3 rounded-lg bg-background/40 px-3 py-2">
                      <div className={cn(
                        "h-2.5 w-2.5 shrink-0 rounded-full",
                        task.status === "completed" ? "bg-emerald-400" :
                        task.status === "inprogress" ? "bg-amber-400" :
                        task.status === "pending" ? "bg-rose-400" : "bg-blue-400"
                      )} />
                      <span className="flex-1 truncate text-xs font-medium text-foreground">{task.title}</span>
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-medium",
                        task.status === "completed" ? "bg-emerald-500/10 text-emerald-400" :
                        task.status === "inprogress" ? "bg-amber-500/10 text-amber-400" :
                        task.status === "pending" ? "bg-rose-500/10 text-rose-400" : "bg-blue-500/10 text-blue-400"
                      )}>
                        {task.status}
                      </span>
                      {task.source_name && (
                        <span className="rounded bg-muted/60 px-1.5 py-0.5 text-[9px] text-muted-foreground">{task.source_name}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="text-center py-16 text-muted-foreground">
            <p>Could not load dashboard data</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => loadStats(true)}>Retry</Button>
          </div>
        )}
      </div>

      {/* Floating Agent Chat Panel */}
      {agentOpen && (
        <section className="fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:bottom-6 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
                <BrainCircuit className="h-3.5 w-3.5 text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">Master Agent</p>
                <p className="text-[10px] text-muted-foreground">
                  {lastDelegation ? `Last: ${lastDelegation}` : "Ask anything"}
                </p>
              </div>
            </div>
            <Button type="button" variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => setAgentOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="mb-3 min-h-0 flex-1 space-y-2 overflow-y-auto rounded-xl border border-border/30 bg-background/40 p-2 sm:p-3">
            {messages.map((msg, i) => (
              <div
                key={`${msg.role}-${i}`}
                className={cn(
                  "max-w-[90%] rounded-xl px-3 py-2 text-[13px] leading-relaxed",
                  msg.role === "user"
                    ? "ml-auto bg-primary/15 text-foreground"
                    : "mr-auto bg-muted/50 text-foreground"
                )}
              >
                {msg.role === "assistant" && <Bot className="mr-1 inline h-3 w-3 text-primary" />}
                {msg.content}
              </div>
            ))}
            {sending && (
              <div className="mr-auto flex items-center gap-1.5 rounded-xl bg-muted/50 px-3 py-2">
                <Loader2 className="h-3 w-3 animate-spin text-primary" />
                <span className="text-[11px] text-muted-foreground">Thinking...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {chatError && (
            <p className="mb-2 rounded-lg border border-rose-500/20 bg-rose-500/10 px-2.5 py-1.5 text-[11px] text-rose-400">
              {chatError}
            </p>
          )}

          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              placeholder="Ask Master Agent..."
              className="flex-1 rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
              disabled={sending}
            />
            <Button type="button" size="sm" className="shrink-0" onClick={() => handleSend()} disabled={!canSend}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </section>
      )}
    </div>
  )
}
