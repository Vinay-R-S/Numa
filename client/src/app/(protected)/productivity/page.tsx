"use client"

import React, { useCallback, useEffect, useState } from "react"
import Image from "next/image"
import {
  Code2,
  ExternalLink,
  GitBranch,
  GitFork,
  GitPullRequest,
  Loader2,
  RefreshCw,
  Star,
  Trophy,
  Unlink,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  type GitHubAuthStatus,
  type GitHubStats,
  type LeetCodeStats,
  connectGitHub,
  connectGitHubToken,
  disconnectGitHub,
  getGitHubStats,
  getGitHubStatus,
  getLeetCodeStats,
} from "@/components/productivity/productivityApi"

// ── Stat Chip ───────────────────────────────────────────────────────────────────

function StatChip({
  icon: Icon,
  label,
  value,
  color = "text-primary",
}: {
  icon: React.ElementType
  label: string
  value: string | number
  color?: string
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-border/40 bg-background/40 p-3 min-w-0">
      <Icon className={cn("h-4 w-4", color)} />
      <span className="text-lg font-black text-foreground tabular-nums">{value}</span>
      <span className="text-[10px] text-muted-foreground font-medium truncate">{label}</span>
    </div>
  )
}

// ── Difficulty Bar ──────────────────────────────────────────────────────────────

function DifficultyBar({
  label,
  solved,
  total,
  color,
  bgColor,
}: {
  label: string
  solved: number
  total: number
  color: string
  bgColor: string
}) {
  const pct = total > 0 ? Math.round((solved / total) * 100) : 0
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className={cn("text-xs font-semibold", color)}>{label}</span>
        <span className="text-xs text-muted-foreground tabular-nums">
          {solved} <span className="text-muted-foreground/50">/ {total}</span>
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-border/20 overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", bgColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ── GitHub Section ──────────────────────────────────────────────────────────────

function GitHubSection() {
  const [status, setStatus] = useState<GitHubAuthStatus | null>(null)
  const [stats, setStats] = useState<GitHubStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [connectingToken, setConnectingToken] = useState(false)
  const [token, setToken] = useState("")
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (force = false) => {
    if (force) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)
    try {
      const s = await getGitHubStatus()
      setStatus(s)
      if (s.connected) {
        const st = await getGitHubStats(force)
        setStats(st)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load GitHub data")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleConnect = async () => {
    try {
      const url = await connectGitHub()
      window.location.href = url
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect")
    }
  }

  const handleTokenConnect = async () => {
    const trimmed = token.trim()
    if (!trimmed) {
      setError("Paste a GitHub token first")
      return
    }

    setConnectingToken(true)
    setError(null)
    try {
      const s = await connectGitHubToken(trimmed)
      setToken("")
      setStatus(s)
      const st = await getGitHubStats(true)
      setStats(st)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect GitHub token")
    } finally {
      setConnectingToken(false)
    }
  }

  const handleDisconnect = async () => {
    try {
      await disconnectGitHub()
      setStatus({ connected: false })
      setStats(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect")
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-3">
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
        <Button variant="ghost" size="sm" onClick={() => void load()}>
          Retry
        </Button>
      </div>
    )
  }

  if (!status?.connected) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-10">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/50 ring-1 ring-border/40">
          <GitBranch className="h-7 w-7 text-muted-foreground" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-foreground">GitHub not connected</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Connect your GitHub account to track contributions
          </p>
        </div>
        <Button size="sm" onClick={() => void handleConnect()} className="gap-2">
          <GitBranch className="h-4 w-4" />
          Connect with OAuth
        </Button>
        <div className="w-full max-w-md space-y-2 rounded-xl border border-border/40 bg-background/40 p-3">
          <label className="text-xs font-semibold text-foreground">
            Or connect with a GitHub token
          </label>
          <div className="flex gap-2">
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="github_pat_... or ghp_..."
              className="min-w-0 flex-1 rounded-lg border border-border/60 bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            <Button
              type="button"
              size="sm"
              onClick={() => void handleTokenConnect()}
              disabled={connectingToken}
            >
              {connectingToken ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Connect"}
            </Button>
          </div>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Use a fine-grained token with repository read access, or a classic token with repo and read:user.
            This is the most reliable local-dev option for private repos and commit history.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* User info + disconnect */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {stats?.avatar_url ? (
            <Image
              src={stats.avatar_url}
              alt={stats.username}
              width={40}
              height={40}
              unoptimized
              className="h-10 w-10 rounded-full ring-2 ring-border/40"
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 ring-2 ring-border/40">
              <GitBranch className="h-5 w-5 text-primary" />
            </div>
          )}
          <div>
            <p className="text-sm font-bold text-foreground">{stats?.username}</p>
            <p className="text-[11px] text-muted-foreground">
              {stats?.followers} followers &middot; {stats?.following} following
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void load(true)}
          disabled={refreshing}
          className="text-muted-foreground hover:text-foreground gap-1.5"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
          <span className="hidden sm:inline">{refreshing ? "Refreshing" : "Refresh"}</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void handleDisconnect()}
          className="text-muted-foreground hover:text-destructive gap-1.5"
        >
          <Unlink className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Disconnect</span>
        </Button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <StatChip icon={Code2} label="Commits Today" value={stats?.total_commits_today ?? 0} color="text-emerald-400" />
        <StatChip icon={Code2} label="Commits This Week" value={stats?.total_commits_week ?? 0} color="text-cyan-400" />
        <StatChip icon={GitPullRequest} label="Open PRs" value={stats?.open_prs ?? 0} color="text-purple-400" />
        <StatChip icon={GitFork} label="Total Repos" value={(stats?.public_repos ?? 0) + (stats?.private_repos ?? 0)} color="text-amber-400" />
      </div>

      {/* Recent repos */}
      {stats?.recent_repos && stats.recent_repos.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
            Recent Repositories
          </h4>
          <div className="space-y-1.5">
            {stats.recent_repos.slice(0, 6).map((repo) => (
              <a
                key={repo.full_name}
                href={repo.html_url || `https://github.com/${repo.full_name}`}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-3 rounded-lg border border-border/30 bg-background/30 px-3 py-2.5 transition-colors hover:border-border/60 hover:bg-background/60"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-foreground truncate">
                      {repo.name}
                    </p>
                    {repo.private && (
                      <span className="shrink-0 rounded-full border border-border/40 bg-muted/50 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                        Private
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 flex items-center gap-3 text-[11px] text-muted-foreground">
                    {repo.language && (
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-primary/60" />
                        {repo.language}
                      </span>
                    )}
                    <span className="flex items-center gap-0.5">
                      <Star className="h-3 w-3" /> {repo.stars}
                    </span>
                    <span className="flex items-center gap-0.5">
                      <GitFork className="h-3 w-3" /> {repo.forks}
                    </span>
                  </div>
                </div>
                <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground/40 transition-colors group-hover:text-foreground" />
              </a>
            ))}
          </div>
        </div>
      )}

      {stats?.recent_commits && stats.recent_commits.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
            Recent Commits
          </h4>
          <div className="space-y-1.5">
            {stats.recent_commits.slice(0, 8).map((commit) => (
              <a
                key={`${commit.repo}-${commit.sha}`}
                href={commit.html_url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-lg border border-border/30 bg-background/30 px-3 py-2.5 transition-colors hover:border-border/60 hover:bg-background/60"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="min-w-0 truncate text-sm font-semibold text-foreground">
                    {commit.message || "Commit"}
                  </p>
                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                    {commit.sha}
                  </span>
                </div>
                <p className="mt-1 truncate text-[11px] text-muted-foreground">
                  {commit.repo}
                  {commit.date ? ` - ${new Date(commit.date).toLocaleDateString()}` : ""}
                </p>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── LeetCode Section ────────────────────────────────────────────────────────────

const LC_KEY = "numa_leetcode_username"

function LeetCodeSection() {
  const [username, setUsername] = useState("")
  const [stats, setStats] = useState<LeetCodeStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const saved = localStorage.getItem(LC_KEY) || ""
    if (saved) {
      setUsername(saved)
      return
    }
    const token = localStorage.getItem("numa_token")
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    fetch(`${base}/api/ai-settings/integration-keys`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data) return
        if (data.leetcode_username_value) {
          setUsername(data.leetcode_username_value)
          localStorage.setItem(LC_KEY, data.leetcode_username_value)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const fetchStats = useCallback(async (user: string) => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const s = await getLeetCodeStats(user)
      setStats(s)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load LeetCode data")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (username) void fetchStats(username)
  }, [username, fetchStats])

  const totalProblems = stats
    ? Math.max(stats.total_solved, stats.easy_solved + stats.medium_solved + stats.hard_solved)
    : 0

  return (
    <div className="space-y-5">
      {error && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading && !stats && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {!username && !loading && (
        <div className="flex flex-col items-center justify-center gap-4 py-10">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 ring-1 ring-amber-500/20">
            <Trophy className="h-7 w-7 text-amber-400" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-foreground">Track your LeetCode</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Add your LeetCode username in{" "}
              <a href="/settings" className="text-primary underline underline-offset-2 hover:text-primary/80">Settings → Integration Keys</a>
              {" "}to see your progress
            </p>
          </div>
        </div>
      )}

      {stats && (
        <div className="space-y-5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">Tracking:</span>
            <span className="text-xs font-semibold text-foreground">{stats.username}</span>
          </div>
          {/* Total + Ranking + Acceptance */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:gap-2.5">
            <div className="flex flex-row items-center gap-3 rounded-xl border border-border/40 bg-background/40 p-3 sm:flex-col sm:gap-1">
              <span className="text-xl font-black text-foreground tabular-nums sm:text-2xl">{stats.total_solved}</span>
              <span className="text-xs text-muted-foreground font-medium sm:text-[10px]">Solved</span>
            </div>
            <div className="flex flex-row items-center gap-3 rounded-xl border border-border/40 bg-background/40 p-3 sm:flex-col sm:gap-1">
              <span className="text-xl font-black text-foreground tabular-nums sm:text-2xl">{stats.acceptance_rate.toFixed(1)}%</span>
              <span className="text-xs text-muted-foreground font-medium sm:text-[10px]">Acceptance</span>
            </div>
            <div className="flex flex-row items-center gap-3 rounded-xl border border-border/40 bg-background/40 p-3 sm:flex-col sm:gap-1">
              <span className="text-xl font-black text-amber-400 tabular-nums sm:text-2xl">#{stats.ranking.toLocaleString()}</span>
              <span className="text-xs text-muted-foreground font-medium sm:text-[10px]">Ranking</span>
            </div>
          </div>

          {/* Difficulty bars */}
          <div className="space-y-3 rounded-xl border border-border/40 bg-background/30 p-4">
            <DifficultyBar
              label="Easy"
              solved={stats.easy_solved}
              total={totalProblems}
              color="text-emerald-400"
              bgColor="bg-emerald-500"
            />
            <DifficultyBar
              label="Medium"
              solved={stats.medium_solved}
              total={totalProblems}
              color="text-amber-400"
              bgColor="bg-amber-500"
            />
            <DifficultyBar
              label="Hard"
              solved={stats.hard_solved}
              total={totalProblems}
              color="text-red-400"
              bgColor="bg-red-500"
            />
          </div>

          {/* Recent accepted submissions */}
          {stats.recent_submissions && stats.recent_submissions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/60">
                Recent Submissions
              </h4>
              <div className="space-y-1.5">
                {stats.recent_submissions.slice(0, 6).map((sub, i) => (
                  <div
                    key={`${sub.title}-${i}`}
                    className="flex items-center gap-3 rounded-lg border border-border/30 bg-background/30 px-3 py-2.5"
                  >
                    <div
                      className={cn(
                        "h-2 w-2 shrink-0 rounded-full",
                        sub.status === "Accepted" ? "bg-emerald-500" : "bg-red-500",
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground truncate">{sub.title}</p>
                      <p className="text-[11px] text-muted-foreground">
                        {sub.lang} &middot; {sub.timestamp}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold",
                        sub.status === "Accepted"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : "bg-red-500/10 text-red-400",
                      )}
                    >
                      {sub.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────────────────────────

export default function ProductivityPage() {
  return (
    <div className="flex h-full w-full flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
      {/* Header */}
      <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-500/10 ring-1 ring-violet-500/20">
            <Code2 className="h-5 w-5 text-violet-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              Productivity
            </h1>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Track your GitHub contributions and LeetCode progress
            </p>
          </div>
        </div>
      </header>

      {/* Two-column grid */}
      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-2 min-h-0">
        {/* GitHub */}
        <section className="flex flex-col rounded-2xl border border-border/40 bg-card/40 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-border/40 px-5 py-3.5 shrink-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
              <GitBranch className="h-4 w-4 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">GitHub</span>
          </div>
          <div className="flex-1 overflow-y-auto p-5">
            <GitHubSection />
          </div>
        </section>

        {/* LeetCode */}
        <section className="flex flex-col rounded-2xl border border-border/40 bg-card/40 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-border/40 px-5 py-3.5 shrink-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10">
              <Trophy className="h-4 w-4 text-amber-400" />
            </div>
            <span className="text-sm font-semibold text-foreground">LeetCode</span>
          </div>
          <div className="flex-1 overflow-y-auto p-5">
            <LeetCodeSection />
          </div>
        </section>
      </div>
    </div>
  )
}
