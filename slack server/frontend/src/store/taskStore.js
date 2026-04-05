/**
 * Tasks store — CRUD + optimistic updates.
 */
import { create } from 'zustand'
import api from '../lib/api'

export const useTaskStore = create((set, get) => ({
  tasks:   [],
  loading: false,
  error:   null,

  fetchTasks: async (status) => {
    set({ loading: true, error: null })
    try {
      const params = status ? { status } : {}
      const { data } = await api.get('/tasks', { params })
      set({ tasks: data })
    } catch (err) {
      set({ error: err.message })
    } finally {
      set({ loading: false })
    }
  },

  addTask: async (payload) => {
    const { data } = await api.post('/tasks', payload)
    set((s) => ({ tasks: [data, ...s.tasks] }))
    return data
  },

  updateTask: async (id, patch) => {
    const { data } = await api.put(`/tasks/${id}`, patch)
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === id ? data : t)),
    }))
    return data
  },

  deleteTask: async (id) => {
    await api.delete(`/tasks/${id}`)
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) }))
  },

  // Called by Supabase Realtime when a task is inserted from Slack
  realtimeUpsert: (task) => {
    set((s) => {
      const exists = s.tasks.find((t) => t.id === task.id)
      if (exists) {
        return { tasks: s.tasks.map((t) => (t.id === task.id ? task : t)) }
      }
      return { tasks: [task, ...s.tasks] }
    })
  },
}))
