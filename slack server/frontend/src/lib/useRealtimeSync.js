/**
 * Supabase Realtime hook — subscribes to live changes for the current user.
 * Feeds updates into Zustand stores so UI reacts instantly.
 *
 * Usage: call once in App.jsx after authentication.
 */
import { useEffect, useRef } from 'react'
import { supabase } from '../lib/supabase'
import { useAuthStore }      from '../store/authStore'
import { useTaskStore }      from '../store/taskStore'
import { useDashboardStore } from '../store/dashboardStore'

export function useRealtimeSync() {
  const user          = useAuthStore((s) => s.user)
  const realtimeUpsert = useTaskStore ((s) => s.realtimeUpsert)
  const patchDashboard = useDashboardStore((s) => s.patch)
  const channelRef    = useRef(null)

  useEffect(() => {
    if (!user?.id) return

    // Remove any previous subscription
    if (channelRef.current) {
      supabase.removeChannel(channelRef.current)
    }

    const channel = supabase
      .channel(`numa-user-${user.id}`)

      // ── Tasks ──────────────────────────────────────────────────────────────
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tasks', filter: `user_id=eq.${user.id}` },
        (payload) => {
          const task = payload.new || payload.old
          if (payload.eventType === 'DELETE') {
            useTaskStore.setState((s) => ({
              tasks: s.tasks.filter((t) => t.id !== payload.old.id),
            }))
          } else {
            realtimeUpsert(task)
          }
          // Re-fetch dashboard score/counts without full reload
          patchDashboard({}) // triggers re-render; store will reconcile
        },
      )

      // ── Messages ───────────────────────────────────────────────────────────
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `slack_user_id=eq.${user.slack_user_id}`,
        },
        (payload) => {
          // Push new message to dashboard recent_messages
          patchDashboard((prev) => ({
            recent_messages: [payload.new, ...(prev?.recent_messages || [])].slice(0, 10),
          }))
        },
      )

      // ── Nudges ─────────────────────────────────────────────────────────────
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'nudges',
          filter: `user_id=eq.${user.id}`,
        },
        (payload) => {
          patchDashboard((prev) => ({
            unread_nudges: (prev?.unread_nudges || 0) + 1,
          }))
        },
      )

      .subscribe()

    channelRef.current = channel

    return () => {
      supabase.removeChannel(channel)
    }
  }, [user?.id])
}
