import type { KeyboardEvent } from "react"
import { Loader2, Save, Sparkles, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { MOODS } from "../journal.constants"
import type { MoodKey } from "../journal.types"
import { formatEntryDate, formatTime } from "../journal.utils"
import { TagPills } from "./TagPills"

export interface JournalEditorProps {
  title: string
  content: string
  mood: MoodKey | null
  tagsRaw: string
  tags: string[]
  aiSummary: string | null
  isNew: boolean
  entryDate: string
  createdAt: string | null
  updatedAt: string | null
  saving: boolean
  deleting: boolean
  confirmDelete: boolean
  setTitle: (value: string) => void
  setContent: (value: string) => void
  setMood: (value: MoodKey | null) => void
  setTagsRaw: (value: string) => void
  setConfirmDelete: (value: boolean) => void
  removeTag: (tag: string) => void
  handleTagsKeyDown: (e: KeyboardEvent<HTMLInputElement>) => void
  handleSave: () => void | Promise<void>
  handleDelete: () => void | Promise<void>
}

/**
 * The journal entry editor (title, mood, content, tags, AI summary, actions).
 * Renders and dispatches only; all state is owned by the `useJournal` hook.
 */
export function JournalEditor({
  title,
  content,
  mood,
  tagsRaw,
  tags,
  aiSummary,
  isNew,
  entryDate,
  createdAt,
  updatedAt,
  saving,
  deleting,
  confirmDelete,
  setTitle,
  setContent,
  setMood,
  setTagsRaw,
  setConfirmDelete,
  removeTag,
  handleTagsKeyDown,
  handleSave,
  handleDelete,
}: JournalEditorProps) {
  return (
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
            <Sparkles className="h-4 w-4 text-primary" />
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
        <Button onClick={() => void handleSave()} disabled={saving} className="gap-2">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
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
          <span className="ml-2 rounded-full border border-primary/20 bg-primary/10 px-2.5 py-0.5 text-[10px] font-semibold text-primary">
            New
          </span>
        )}
      </div>
    </div>
  )
}
