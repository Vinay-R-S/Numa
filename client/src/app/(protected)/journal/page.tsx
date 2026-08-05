"use client"

import { BookOpen, Loader2, Plus, Sparkles } from "lucide-react"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import {
  EmptyState,
  EntryList,
  JournalEditor,
  useJournal,
} from "@/features/journal"

export default function JournalPage() {
  const {
    entries,
    selectedDate,
    loading,
    error,
    successMsg,
    hasSelection,
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
    autoGenerating,
    confirmDelete,
    setTitle,
    setContent,
    setMood,
    setTagsRaw,
    setConfirmDelete,
    removeTag,
    handleTagsKeyDown,
    handleSelect,
    handleNew,
    handleSave,
    handleDelete,
    handleAutoGenerate,
  } = useJournal()

  return (
    <div className="flex h-full w-full flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
      {/* Header */}
      <header className="flex items-center justify-between rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
            <BookOpen className="h-5 w-5 text-foreground" />
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
          <HeaderActionButton
            icon={autoGenerating ? Loader2 : Sparkles}
            label="Auto Generate"
            loading={autoGenerating}
            active={autoGenerating}
            onClick={() => void handleAutoGenerate()}
            disabled={autoGenerating}
          >
            {autoGenerating ? "Generating..." : "Auto Generate"}
          </HeaderActionButton>
          <HeaderActionButton icon={Plus} label="New Entry" onClick={handleNew} />
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
        <EntryList
          entries={entries}
          loading={loading}
          selectedDate={selectedDate}
          onSelect={handleSelect}
          layout="horizontal"
        />
      </div>

      {/* Main grid */}
      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-4 min-h-0">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex flex-col gap-1.5 overflow-y-auto rounded-2xl border border-border/40 bg-card/40 p-3">
          <p className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
            Entries
          </p>
          <EntryList
            entries={entries}
            loading={loading}
            selectedDate={selectedDate}
            onSelect={handleSelect}
            layout="vertical"
          />
        </aside>

        {/* Content area */}
        <div className="flex flex-col lg:col-span-3 min-h-0">
          {hasSelection ? (
            <JournalEditor
              title={title}
              content={content}
              mood={mood}
              tagsRaw={tagsRaw}
              tags={tags}
              aiSummary={aiSummary}
              isNew={isNew}
              entryDate={entryDate}
              createdAt={createdAt}
              updatedAt={updatedAt}
              saving={saving}
              deleting={deleting}
              confirmDelete={confirmDelete}
              setTitle={setTitle}
              setContent={setContent}
              setMood={setMood}
              setTagsRaw={setTagsRaw}
              setConfirmDelete={setConfirmDelete}
              removeTag={removeTag}
              handleTagsKeyDown={handleTagsKeyDown}
              handleSave={handleSave}
              handleDelete={handleDelete}
            />
          ) : (
            <div className="flex-1 rounded-2xl border border-border/40 bg-card/40">
              <EmptyState />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
