import type { Task, TaskStats } from "./types"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function authHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchTasks(): Promise<Task[]> {
  const res = await fetch(`${API}/tasks`, { headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to fetch tasks")
  return res.json()
}

export async function createTask(
  data: Partial<Task> & { title: string }
): Promise<Task> {
  const res = await fetch(`${API}/tasks`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Failed to create task")
  return res.json()
}

export async function updateTask(id: string, data: Partial<Task>): Promise<Task> {
  const res = await fetch(`${API}/tasks/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error("Failed to update task")
  return res.json()
}

export async function patchTaskStatus(
  id: string,
  status: Task["status"],
  position?: number
): Promise<Task> {
  const res = await fetch(`${API}/tasks/${id}/status`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ status, position }),
  })
  if (!res.ok) throw new Error("Failed to update task status")
  return res.json()
}

export async function deleteTask(id: string): Promise<void> {
  const res = await fetch(`${API}/tasks/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error("Failed to delete task")
}

export async function fetchStats(): Promise<TaskStats> {
  const res = await fetch(`${API}/tasks/stats`, { headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to fetch stats")
  return res.json()
}
