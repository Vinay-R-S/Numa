/**
 * Tasks API (NUMA-111 P4, PLAN 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client. Preserves the prior
 * behavior: a 12s request timeout surfaced as a friendly message, curated
 * fallback error text per endpoint, and a swallowed 404 on delete. Responses
 * are validated with the feature's zod schemas.
 *
 * The timeout is `http`'s own `timeoutMs`, which disarms once the response
 * headers arrive, so a slow body read is not counted against the deadline.
 *
 * Every endpoint here answers with JSON. `http` resolves a body-less or
 * non-JSON 2xx to `undefined` (a proxy that drops the content-type header is
 * enough), which `tasksStore` would then commit as `tasks: undefined` inside
 * its try, crashing the page on the next `tasks.length`; `expectBody` turns
 * that into the endpoint's error instead. `deleteTask` is exempt: it expects
 * an empty body.
 */
import { expectBody, http, ApiError, type RequestOptions } from "@/lib/http"
import type { Task, TaskStats } from "./tasks.types"
import { taskListSchema, taskSchema, taskStatsSchema } from "./tasks.schema"

const REQUEST_TIMEOUT_MS = 12000
const TIMEOUT_MESSAGE = "Request timed out. Please check backend server status."

function timed<T>(options: Omit<RequestOptions<T>, "method" | "body">) {
  return { ...options, timeoutMs: REQUEST_TIMEOUT_MS, timeoutMessage: TIMEOUT_MESSAGE }
}

export function fetchTasks(): Promise<Task[]> {
  const message = "Failed to fetch tasks"
  return expectBody(http.get("/tasks", timed({ schema: taskListSchema, errorMessage: message })), message)
}

export function createTask(data: Partial<Task> & { title: string }): Promise<Task> {
  const message = "Failed to create task"
  return expectBody(http.post("/tasks", data, timed({ schema: taskSchema, errorMessage: message })), message)
}

export function updateTask(id: string, data: Partial<Task>): Promise<Task> {
  const message = "Failed to update task"
  return expectBody(
    http.put(`/tasks/${id}`, data, timed({ schema: taskSchema, errorMessage: message })),
    message
  )
}

export function patchTaskStatus(
  id: string,
  status: Task["status"],
  position?: number
): Promise<Task> {
  const message = "Failed to update task status"
  return expectBody(
    http.patch(
      `/tasks/${id}/status`,
      { status, position },
      timed({ schema: taskSchema, errorMessage: message })
    ),
    message
  )
}

export async function deleteTask(id: string): Promise<void> {
  try {
    await http.del(`/tasks/${id}`, timed({ errorMessage: "Failed to delete task" }))
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return
    throw error
  }
}

export function fetchStats(): Promise<TaskStats> {
  const message = "Failed to fetch stats"
  return expectBody(
    http.get("/tasks/stats", timed({ schema: taskStatsSchema, errorMessage: message })),
    message
  )
}

export function fetchCompletedHistory(): Promise<Task[]> {
  const message = "Failed to fetch task history"
  return expectBody(
    http.get("/tasks/history", timed({ schema: taskListSchema, errorMessage: message })),
    message
  )
}
