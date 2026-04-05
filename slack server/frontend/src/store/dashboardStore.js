/**
 * Dashboard store — today's overview data.
 */
import { create } from 'zustand'
import api from '../lib/api'

export const useDashboardStore = create((set) => ({
  data:    null,
  loading: false,
  error:   null,

  fetchToday: async () => {
    set({ loading: true, error: null })
    try {
      const { data } = await api.get('/dashboard/today')
      set({ data })
    } catch (err) {
      set({ error: err.message })
    } finally {
      set({ loading: false })
    }
  },

  // Patch individual fields when Realtime fires
  patch: (updates) => set((s) => ({ data: s.data ? { ...s.data, ...updates } : s.data })),
}))
