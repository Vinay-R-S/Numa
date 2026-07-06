/**
 * Tasks feature module public surface (NUMA-111 P4, PLAN 5.3 / 21.2).
 *
 * Cross-page task state lives in the `useTasksStore` zustand store
 * (`lib/stores/tasksStore.ts`) as the single source of truth (PLAN 9); it
 * consumes this module's api/types.
 */
export * from "./tasks.types"
export * from "./tasks.api"
export * from "./tasks.schema"

export { KanbanBoard } from "./components/KanbanBoard"
export { AnalyticsDashboard } from "./components/AnalyticsDashboard"
export { TaskDetailSheet } from "./components/TaskDetailSheet"
export { TaskCard } from "./components/TaskCard"
export { TaskDialog } from "./components/TaskDialog"
export { KanbanColumn } from "./components/KanbanColumn"
