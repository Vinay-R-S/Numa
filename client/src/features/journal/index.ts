/**
 * Journal feature module public surface (NUMA-112 P4, PLAN 5.3 / 21.2).
 */
export * from "./journal.types"
export * from "./journal.api"
export * from "./journal.schema"
export * from "./journal.utils"
export { MOODS } from "./journal.constants"
export { useJournal } from "./useJournal"
export type { UseJournalReturn } from "./useJournal"

export { EntryCard } from "./components/EntryCard"
export { EntryList } from "./components/EntryList"
export { EmptyState } from "./components/EmptyState"
export { TagPills } from "./components/TagPills"
export { JournalEditor } from "./components/JournalEditor"
