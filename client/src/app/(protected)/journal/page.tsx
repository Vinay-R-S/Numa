"use client"

import React, { useCallback, useEffect, useState } from "react"
import {
  BookOpen,
  Plus,
  Save,
  Trash2,
  Sparkles,
  Loader2,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  type JournalEntry,
  listJournalEntries,
  getJournalEntry,
  createJournalEntry,
  updateJournalEntry,
  deleteJournalEntry,
  autoGenerateJournal,
} from "@/components/journal/journalApi"

// ── Constants ────────────────────────────────────────────────────────────────────

const MOODS = [
  { key: "great", emoji: "😊", label: "Great" },
  { key: "good", emoji: "🙂", label: "Good" },
  { key: "okay", emoji: "😐", label: "Okay" },
  { key: "bad", emoji: "😔", label: "Bad" },
  { key: "terrible", emoji: "😢", label: "Terrible" },
] as const

type MoodKey = (typeof MOODS)[number]["key"]

function moodEmoji(mood: string | null): string {
  return MOODS.find((m) => m.key === mood)?.emoji ?? ""
}

function todayDateStr(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatSidebarDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00")
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })
}

// ── Sidebar Entry Card ──────────────────────────────────────────────────────────

function EntryCard({
  entry,
  active,
  onClick,
  layout,
}: {
  entry: JournalEntry
  active: boolean
  onClick: () => void
  layout: "vertical" | "horizontal"
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "text-left transition-all",
        layout === "vertical"
          ? "w-full rounded-xl border px-3 py-2.5"
          : "shrink-0 rounded-xl border px-3 py-2 min-w-[140px] max-w-[180px]",
        active
          ? "border-primary/30 bg-primary/10"
          : "border-border/30 bg-background/40 hover:border-border/50 hover:bg-card/60",
      )}
    >
      <div className="flex items-center gap-2 mb-0.5">
        {entry.mood && <span className="text-sm">{moodEmoji(entry.mood)}</span>}
        <span className="text-[10px] text-muted-foreground font-medium">
          {formatSidebarDate(entry.entry_date)}
        </span>
      </div>
      <p className={cn(
        "text-sm font-medium truncate",
        active ? "text-foreground" : "text-foreground/80",
      )}>
        {entry.title || "Untitled"}
      </p>
    </button>
  )
}

// ── Empty State ─────────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
        <BookOpen className="h-8 w-8 text-primary/60" />
      </div>
      <div>
        <h2 className="text-lg font-bold text-foreground mb-1">No entry selected</h2>
        <p className="text-sm text-muted-foreground max-w-xs">
          Select a journal entry from the sidebar, or click &ldquo;New Entry&rdquo; to start writing.
        </p>
      </div>
    </div>
  )
}

// ── Tag Pills ───────────────────────────────────────────────────────────────────

function TagPills({
  tags,
  onRemove,
}: {
  tags: string[]
  onRemove: (tag: string) => void
}) {
  if (tags.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-full border border-border/40 bg-background/60 px-2.5 py-0.5 text-xs text-muted-foreground"
        >
          {tag}
          <button
            type="button"
            onClick={() => onRemove(tag)}
            className="ml-0.5 rounded-full p-0.5 hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <X className="h-2.5 w-2.5" />
          </button>
        </span>
      ))}
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────────────────────────

export default function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Editor state
  const [title, setTitle] = useState("")
  const [content, setContent] = useState("")
  const [mood, setMood] = useState<MoodKey | null>(null)
  const [tagsRaw, setTagsRaw] = useState("")
  const [tags, setTags] = useState<string[]>([])
  const [aiSummary, setAiSummary] = useState<string | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [entryDate, setEntryDate] = useState(todayDateStr())

  // Timestamps
  const [createdAt, setCreatedAt] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)

  // Action states
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [autoGenerating, setAutoGenerating] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // ── Load entries ──────────────────────────────────────────────────────────────

  const loadEntries = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listJournalEntries(50, 0)
      setEntries(data.entries)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load entries")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadEntries()
  }, [loadEntries])

  // ── Flash success message ─────────────────────────────────────────────────────

  useEffect(() => {
    if (!successMsg) return
    const timer = setTimeout(() => setSuccessMsg(null), 2500)
    return () => clearTimeout(timer)
  }, [successMsg])

  // ── Populate editor from entry ────────────────────────────────────────────────

  const populateEditor = useCallback((entry: JournalEntry) => {
    setTitle(entry.title)
    setContent(entry.content)
    setMood((entry.mood as MoodKey) || null)
    setTags(entry.tags || [])
    setTagsRaw("")
    setAiSummary(entry.ai_summary || null)
    setEntryDate(entry.entry_date)
    setCreatedAt(entry.created_at || null)
    setUpdatedAt(entry.updated_at || null)
    setIsNew(false)
    setConfirmDelete(false)
  }, [])

  // ── Select an entry ───────────────────────────────────────────────────────────

  const handleSelect = useCallback(
    async (date: string) => {
      setSelectedDate(date)
      setError(null)
      try {
        const entry = await getJournalEntry(date)
        populateEditor(entry)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load entry")
      }
    },
    [populateEditor],
  )

  // ── New entry ─────────────────────────────────────────────────────────────────

  const handleNew = useCallback(() => {
    const today = todayDateStr()
    setSelectedDate(today)
    setTitle("")
    setContent("")
    setMood(null)
    setTags([])
    setTagsRaw("")
    setAiSummary(null)
    setEntryDate(today)
    setCreatedAt(null)
    setUpdatedAt(null)
    setIsNew(true)
    setConfirmDelete(false)
    setError(null)
  }, [])

  // ── Tags input ────────────────────────────────────────────────────────────────

  const handleTagsKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      const val = tagsRaw.trim().replace(/,+$/, "").trim()
      if (val && !tags.includes(val)) {
        setTags((prev) => [...prev, val])
      }
      setTagsRaw("")
    }
  }

  const removeTag = (tag: string) => setTags((prev) => prev.filter((t) => t !== tag))

  // ── Save ──────────────────────────────────────────────────────────────────────

  const handleSave = async () => {
    if (!title.trim()) {
      setError("Title is required")
      return
    }
    setSaving(true)
    setError(null)
    try {
      if (isNew) {
        const created = await createJournalEntry({
          title: title.trim(),
          content,
          mood,
          entry_date: entryDate,
          tags,
        })
        populateEditor(created)
        setSelectedDate(created.entry_date)
      } else {
        await updateJournalEntry(entryDate, {
          title: title.trim(),
          content,
          mood,
          tags,
        })
      }
      await loadEntries()
      setSuccessMsg("Entry saved!")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save entry")
    } finally {
      setSaving(false)
    }
  }

  // ── Delete ────────────────────────────────────────────────────────────────────

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setDeleting(true)
    setError(null)
    try {
      await deleteJournalEntry(entryDate)
      setSelectedDate(null)
      setConfirmDelete(false)
      await loadEntries()
      setSuccessMsg("Entry deleted")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete entry")
    } finally {
      setDeleting(false)
    }
  }

  // ── Summarize ─────────────────────────────────────────────────────────────────

  // ── Auto Generate ─────────────────────────────────────────────────────────────

  const handleAutoGenerate = async () => {
    setAutoGenerating(true)
    setError(null)
    try {
      const entry = await autoGenerateJournal()
      populateEditor(entry)
      setSelectedDate(entry.entry_date)
      await loadEntries()
      setSuccessMsg("Journal auto-generated!")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to auto-generate journal")
    } finally {
      setAutoGenerating(false)
    }
  }

  // ── Format timestamps ────────────────────────────────────────────────────────

  const formatEntryDate = (dateStr: string): string => {
    const d = new Date(dateStr + "T00:00:00")
    return d.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  }

  const formatTime = (isoStr: string): string => {
    const d = new Date(isoStr)
    return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  const hasSelection = selectedDate !== null

  return (
    <div className="flex h-full w-full flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
      {/* Header */}
      <header className="flex items-center justify-between rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 ring-1 ring-amber-500/20">
            <BookOpen className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              Journal
            </h1>
            <p className="text-xs text-muted-foreground sm:text-sm">
              Capture your thoughts, moods &amp; reflections
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => void handleAutoGenerate()}
            disabled={autoGenerating}
            className="gap-2 bg-amber-500 text-black shadow-sm hover:bg-amber-400"
          >
            {autoGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">
              {autoGenerating ? "Generating..." : "Auto Generate"}
            </span>
          </Button>
          <Button size="sm" onClick={handleNew} className="gap-2">
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">New Entry</span>
          </Button>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Success toast */}
      {successMsg && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-400">
          {successMsg}
        </div>
      )}

      {/* Mobile: horizontal scroll entry list */}
      <div className="flex gap-2 overflow-x-auto pb-1 lg:hidden">
        {loading ? (
          <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : entries.length === 0 ? (
          <p className="px-2 py-3 text-sm text-muted-foreground">No entries yet</p>
        ) : (
          entries.map((entry) => (
            <EntryCard
              key={entry.id}
              entry={entry}
              active={selectedDate === entry.entry_date}
              onClick={() => void handleSelect(entry.entry_date)}
              layout="horizontal"
            />
          ))
        )}
      </div>

      {/* Main grid */}
      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-4 min-h-0">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex flex-col gap-1.5 overflow-y-auto rounded-2xl border border-border/40 bg-card/40 p-3">
          <p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Entries
          </p>
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : entries.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No entries yet</p>
          ) : (
            entries.map((entry) => (
              <EntryCard
                key={entry.id}
                entry={entry}
                active={selectedDate === entry.entry_date}
                onClick={() => void handleSelect(entry.entry_date)}
                layout="vertical"
              />
            ))
          )}
        </aside>

        {/* Content area */}
        <div className="flex flex-col lg:col-span-3 min-h-0">
          {!hasSelection ? (
            <div className="flex-1 rounded-2xl border border-border/40 bg-card/40">
              <EmptyState />
            </div>
          ) : (
            <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
              {/* Title */}
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Entry title…"
                className="rounded-xl border border-border/40 bg-card/40 px-5 py-4 text-xl font-bold text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30"
              />

              {/* Entry date & timestamps */}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-muted-foreground">
                <span className="font-medium">{formatEntryDate(entryDate)}</span>
                {createdAt && (
                  <>
                    <span className="text-border">•</span>
                    <span>Created at {formatTime(createdAt)}</span>
                  </>
                )}
                {updatedAt && createdAt && updatedAt !== createdAt && (
                  <>
                    <span className="text-border">•</span>
                    <span>Updated at {formatTime(updatedAt)}</span>
                  </>
                )}
              </div>

              {/* Mood selector */}
              <div className="rounded-xl border border-border/40 bg-card/40 px-5 py-3">
                <p className="text-xs font-semibold text-muted-foreground mb-2">How are you feeling?</p>
                <div className="flex flex-wrap gap-2">
                  {MOODS.map((m) => (
                    <button
                      key={m.key}
                      type="button"
                      onClick={() => setMood(mood === m.key ? null : m.key)}
                      className={cn(
                        "flex flex-col items-center gap-0.5 rounded-xl border px-2 py-1.5 transition-all sm:gap-1 sm:px-3 sm:py-2",
                        mood === m.key
                          ? "border-primary/30 bg-primary/10 scale-105"
                          : "border-border/30 bg-background/40 hover:border-border/50 hover:bg-card/60",
                      )}
                    >
                      <span className="text-lg sm:text-xl">{m.emoji}</span>
                      <span className={cn(
                        "text-[9px] font-medium sm:text-[10px]",
                        mood === m.key ? "text-foreground" : "text-muted-foreground",
                      )}>
                        {m.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Content textarea */}
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Write your thoughts…"
                rows={8}
                className="flex-1 min-h-[150px] rounded-xl border border-border/40 bg-card/40 px-3 py-3 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 resize-y leading-relaxed sm:min-h-[200px] sm:px-5 sm:py-4"
              />

              {/* Tags */}
              <div className="rounded-xl border border-border/40 bg-card/40 px-5 py-3">
                <p className="text-xs font-semibold text-muted-foreground mb-2">Tags</p>
                <TagPills tags={tags} onRemove={removeTag} />
                <input
                  value={tagsRaw}
                  onChange={(e) => setTagsRaw(e.target.value)}
                  onKeyDown={handleTagsKeyDown}
                  placeholder="Type a tag and press Enter…"
                  className="mt-2 w-full rounded-lg border border-border/30 bg-background/40 px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30"
                />
              </div>

              {/* AI Summary */}
              <div className="rounded-xl border border-border/40 bg-card/40 px-5 py-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-amber-400" />
                    <p className="text-xs font-semibold text-muted-foreground">AI Summary</p>
                  </div>
                </div>
                {aiSummary ? (
                  <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-line">
                    {aiSummary}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground/50 italic">
                    Auto Generate will create the entry and summary from your day data.
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="flex flex-wrap items-center gap-2 pb-2">
                <Button
                  onClick={() => void handleSave()}
                  disabled={saving}
                  className="gap-2"
                >
                  {saving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  {saving ? "Saving…" : "Save"}
                </Button>

                {!isNew && (
                  <Button
                    variant={confirmDelete ? "destructive" : "ghost"}
                    onClick={() => void handleDelete()}
                    disabled={deleting}
                    className="gap-2 text-muted-foreground hover:text-destructive"
                  >
                    {deleting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                    {confirmDelete ? "Confirm Delete" : "Delete"}
                  </Button>
                )}

                {confirmDelete && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmDelete(false)}
                    className="text-xs text-muted-foreground"
                  >
                    Cancel
                  </Button>
                )}

                {isNew && (
                  <span className="ml-2 rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-amber-400">
                    New
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
