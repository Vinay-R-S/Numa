/**
 * Tasks API (NUMA-111 P4, PLAN 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client. Preserves the prior
 * behavior: a 12s request timeout surfaced as a friendly message, curated
 * fallback error text per endpoint, and a swallowed 404 on delete. Responses
 * are validated with the feature's zod schemas.
 */
import { http, ApiError } from "@/lib/http"
import type { Task, TaskStats } from "./tasks.types"
import { taskListSchema, taskSchema, taskStatsSchema } from "./tasks.schema"

const REQUEST_TIMEOUT_MS = 12000

async function withTimeout<T>(run: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    return await run(controller.signal)
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Request timed out. Please check backend server status.")
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

export function fetchTasks(): Promise<Task[]> {
  return withTimeout((signal) =>
    http.get("/tasks", { signal, schema: taskListSchema, errorMessage: "Failed to fetch tasks" })
  )
}

export function createTask(data: Partial<Task> & { title: string }): Promise<Task> {
  return withTimeout((signal) =>
    http.post("/tasks", data, { signal, schema: taskSchema, errorMessage: "Failed to create task" })
  )
}

export function updateTask(id: string, data: Partial<Task>): Promise<Task> {
  return withTimeout((signal) =>
    http.put(`/tasks/${id}`, data, { signal, schema: taskSchema, errorMessage: "Failed to update task" })
  )
}

export function patchTaskStatus(
  id: string,
  status: Task["status"],
  position?: number
): Promise<Task> {
  return withTimeout((signal) =>
    http.patch(
      `/tasks/${id}/status`,
      { status, position },
      { signal, schema: taskSchema, errorMessage: "Failed to update task status" }
    )
  )
}

export function deleteTask(id: string): Promise<void> {
  return withTimeout(async (signal) => {
    try {
      await http.del(`/tasks/${id}`, { signal, errorMessage: "Failed to delete task" })
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return
      throw error
    }
  })
}

export function fetchStats(): Promise<TaskStats> {
  return withTimeout((signal) =>
    http.get("/tasks/stats", { signal, schema: taskStatsSchema, errorMessage: "Failed to fetch stats" })
  )
}

export function fetchCompletedHistory(): Promise<Task[]> {
  return withTimeout((signal) =>
    http.get("/tasks/history", {
      signal,
      schema: taskListSchema,
      errorMessage: "Failed to fetch task history",
    })
  )
}
