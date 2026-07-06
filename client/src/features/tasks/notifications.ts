const timers = new Map<string, ReturnType<typeof setTimeout>>()

export async function requestNotificationPermission(): Promise<boolean> {
  if (typeof window === "undefined" || !("Notification" in window)) return false
  if (Notification.permission === "granted") return true
  if (Notification.permission === "denied") return false
  const result = await Notification.requestPermission()
  return result === "granted"
}

export function scheduleReminder(taskId: string, title: string, reminderAt: string | null | undefined): void {
  if (!reminderAt) return
  if (typeof window === "undefined" || !("Notification" in window)) return

  const fireAt = new Date(reminderAt).getTime()
  const msUntil = fireAt - Date.now()

  // Cancel any existing timer for this task
  const existing = timers.get(taskId)
  if (existing !== undefined) clearTimeout(existing)

  if (msUntil <= 0) return // Already past

  const timer = setTimeout(() => {
    if (Notification.permission === "granted") {
      new Notification(`Reminder: ${title}`, {
        body: "You have a task reminder.",
        icon: "/favicon.ico",
      })
    }
    timers.delete(taskId)
  }, msUntil)

  timers.set(taskId, timer)
}

export function cancelReminder(taskId: string): void {
  const timer = timers.get(taskId)
  if (timer !== undefined) {
    clearTimeout(timer)
    timers.delete(taskId)
  }
}
