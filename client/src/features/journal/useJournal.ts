/**
 * Journal data hook (NUMA-112 P4, PLAN 21.2).
 *
 * Owns all journal page state (entry list, editor fields, action flags) and the
 * fetch/mutation orchestration. The page consumes only this hook and composes
 * presentational components.
 */
import { useCallback, useEffect, useState } from "react"
import type { KeyboardEvent } from "react"
import {
  autoGenerateJournal,
  createJournalEntry,
  deleteJournalEntry,
  getJournalEntry,
  listJournalEntries,
  updateJournalEntry,
} from "./journal.api"
import type { JournalEntry, MoodKey } from "./journal.types"
import { todayDateStr } from "./journal.utils"

export function useJournal() {
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

  useEffect(() => {
    if (!successMsg) return undefined
    const timer = setTimeout(() => setSuccessMsg(null), 2500)
    return () => clearTimeout(timer)
  }, [successMsg])

  // Load an entry into the editor, or reset to a blank new-entry state (null).
  const applyEditor = useCallback((entry: JournalEntry | null) => {
    setTitle(entry?.title ?? "")
    setContent(entry?.content ?? "")
    setMood((entry?.mood as MoodKey) || null)
    setTags(entry?.tags || [])
    setTagsRaw("")
    setAiSummary(entry?.ai_summary || null)
    setEntryDate(entry?.entry_date || todayDateStr())
    setCreatedAt(entry?.created_at || null)
    setUpdatedAt(entry?.updated_at || null)
    setIsNew(entry === null)
    setConfirmDelete(false)
  }, [])

  const handleSelect = useCallback(
    async (date: string) => {
      setSelectedDate(date)
      setError(null)
      try {
        const entry = await getJournalEntry(date)
        applyEditor(entry)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load entry")
      }
    },
    [applyEditor],
  )

  const handleNew = useCallback(() => {
    setSelectedDate(todayDateStr())
    applyEditor(null)
    setError(null)
  }, [applyEditor])

  const handleTagsKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault()
        const val = tagsRaw.trim().replace(/,+$/, "").trim()
        if (val && !tags.includes(val)) {
          setTags((prev) => [...prev, val])
        }
        setTagsRaw("")
      }
    },
    [tagsRaw, tags],
  )

  const removeTag = useCallback((tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag))
  }, [])

  const handleSave = useCallback(async () => {
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
        applyEditor(created)
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
  }, [title, content, mood, entryDate, tags, isNew, applyEditor, loadEntries])

  const handleDelete = useCallback(async () => {
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
  }, [confirmDelete, entryDate, loadEntries])

  const handleAutoGenerate = useCallback(async () => {
    setAutoGenerating(true)
    setError(null)
    try {
      const entry = await autoGenerateJournal()
      applyEditor(entry)
      setSelectedDate(entry.entry_date)
      await loadEntries()
      setSuccessMsg("Journal auto-generated!")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to auto-generate journal")
    } finally {
      setAutoGenerating(false)
    }
  }, [applyEditor, loadEntries])

  return {
    entries,
    selectedDate,
    loading,
    error,
    successMsg,
    hasSelection: selectedDate !== null,
    // editor fields
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
    // action flags
    saving,
    deleting,
    autoGenerating,
    confirmDelete,
    // setters + handlers
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
  }
}

export type UseJournalReturn = ReturnType<typeof useJournal>
