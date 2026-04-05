/**
 * Auth store — manages JWT token and current user.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../lib/api'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user:  null,
      isAuthenticated: false,

      setToken: (token) => {
        localStorage.setItem('numa_token', token)
        set({ token, isAuthenticated: !!token })
      },

      setUser: (user) => set({ user }),

      fetchMe: async () => {
        try {
          const { data } = await api.get('/auth/me')
          set({ user: data, isAuthenticated: true })
        } catch {
          get().logout()
        }
      },

      logout: () => {
        localStorage.removeItem('numa_token')
        set({ token: null, user: null, isAuthenticated: false })
      },
    }),
    {
      name: 'numa-auth',
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
)
