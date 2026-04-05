/**
 * Axios instance with JWT auth and base URL.
 * Token is read from Zustand auth store on every request.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach JWT token ─────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    // Lazy-import inside interceptor to avoid circular module issues
    const token = localStorage.getItem('numa_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── Response interceptor: handle 401 globally ────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired — clear and redirect to login
      localStorage.removeItem('numa_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default api
