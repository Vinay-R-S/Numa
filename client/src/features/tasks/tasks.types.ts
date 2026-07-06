export type TaskStatus = "planned" | "inprogress" | "completed" | "pending"
export type TaskPriority = "low" | "medium" | "high" | "urgent"

export interface Task {
  id: string
  user_id: string
  title: string
  description?: string | null
  status: TaskStatus
  priority?: TaskPriority | null
  due_date?: string | null
  reminder_at?: string | null
  source_name?: string | null
  source_logo?: string | null
  external_ref?: string | null
  position: number
  completed_at?: string | null
  created_at: string
  updated_at: string
}

export interface TaskStats {
  total: number
  streak: number
  by_status: { status: string; count: number }[]
  daily: { date: string; count: number }[]
  weekly: { date: string; count: number }[]
  monthly: { date: string; count: number }[]
  yearly: { date: string; count: number }[]
}

export const COLUMN_CONFIG: Record<
  TaskStatus,
  { label: string; color: string; bgColor: string; borderColor: string }
> = {
  planned: {
    label: "Planned",
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
  },
  inprogress: {
    label: "In Progress",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
  },
  completed: {
    label: "Completed",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
  },
  pending: {
    label: "Pending",
    color: "text-rose-400",
    bgColor: "bg-rose-500/10",
    borderColor: "border-rose-500/30",
  },
}

export const PRIORITY_CONFIG: Record<
  TaskPriority,
  { label: string; color: string; dot: string }
> = {
  low: { label: "Low", color: "text-slate-400", dot: "bg-slate-400" },
  medium: { label: "Medium", color: "text-sky-400", dot: "bg-sky-400" },
  high: { label: "High", color: "text-orange-400", dot: "bg-orange-400" },
  urgent: { label: "Urgent", color: "text-red-400", dot: "bg-red-400" },
}
