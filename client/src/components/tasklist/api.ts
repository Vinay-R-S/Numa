import type { Task, TaskStats } from "./types"

const REQUEST_TIMEOUT_MS = 12000

function authHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function requestWithTimeout(url: string, init: RequestInit = {}): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Request timed out. Please check backend server status.")
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}

async function parseError(response: Response, fallbackMessage: string): Promise<Error> {
  try {
    const body = await response.json()
    if (typeof body?.detail === "string" && body.detail.trim()) {
      return new Error(body.detail)
    }
  } catch {
    // ignore non-JSON error response bodies
  }

  return new Error(fallbackMessage)
}

export async function fetchTasks(): Promise<Task[]> {
  const res = await requestWithTimeout(`/api/tasks`, { headers: authHeaders() })
  if (!res.ok) throw await parseError(res, "Failed to fetch tasks")
  return res.json()
}

export async function createTask(
  data: Partial<Task> & { title: string }
): Promise<Task> {
  const res = await requestWithTimeout(`/api/tasks`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw await parseError(res, "Failed to create task")
  return res.json()
}

export async function updateTask(id: string, data: Partial<Task>): Promise<Task> {
  const res = await requestWithTimeout(`/api/tasks/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw await parseError(res, "Failed to update task")
  return res.json()
}

export async function patchTaskStatus(
  id: string,
  status: Task["status"],
  position?: number
): Promise<Task> {
  const res = await requestWithTimeout(`/api/tasks/${id}/status`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ status, position }),
  })
  if (!res.ok) throw await parseError(res, "Failed to update task status")
  return res.json()
}

export async function deleteTask(id: string): Promise<void> {
  const res = await requestWithTimeout(`/api/tasks/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  })
  if (!res.ok) throw await parseError(res, "Failed to delete task")
}

export async function fetchStats(): Promise<TaskStats> {
  const res = await requestWithTimeout(`/api/tasks/stats`, { headers: authHeaders() })
  if (!res.ok) throw await parseError(res, "Failed to fetch stats")
  return res.json()
}

export async function fetchCompletedHistory(): Promise<Task[]> {
  const res = await requestWithTimeout(`/api/tasks/history`, { headers: authHeaders() })
  if (!res.ok) throw await parseError(res, "Failed to fetch task history")
  return res.json()
}
