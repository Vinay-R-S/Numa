/**
 * App.jsx — root React Router setup with protected layout.
 */
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useRealtimeSync } from './lib/useRealtimeSync'

// Layout
import Sidebar from './components/Sidebar'
import TopBar  from './components/TopBar'

// Pages
import LoginPage        from './pages/LoginPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import DashboardPage    from './pages/DashboardPage'
import MessagesPage     from './pages/MessagesPage'
import TasksPage        from './pages/TasksPage'
import SchedulePage     from './pages/SchedulePage'
import AnalyticsPage    from './pages/AnalyticsPage'
import SettingsPage     from './pages/SettingsPage'
import CommandPage     from './pages/CommandPage'

/** Protected layout — wraps all authenticated pages. */
function AppLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const token = useAuthStore((s) => s.token)
  const hasSession = isAuthenticated || !!token || !!localStorage.getItem('numa_token')

  // Realtime subscriptions are started here so they are always active
  // while the user is logged in, regardless of which page they visit.
  useRealtimeSync()

  if (!hasSession) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-screen bg-gray-950 text-gray-100">
      <Sidebar />
      <div className="flex-1 ml-60">
        <Outlet />
      </div>
    </div>
  )
}

/** Public-only guard — redirect to /dashboard if already logged in. */
function PublicRoute({ children }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const token = useAuthStore((s) => s.token)
  const hasSession = isAuthenticated || !!token || !!localStorage.getItem('numa_token')
  return hasSession ? <Navigate to="/dashboard" replace /> : children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route
          path="/login"
          element={<PublicRoute><LoginPage /></PublicRoute>}
        />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />

        {/* Protected */}
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/"           element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard"  element={<DashboardPage />} />
          <Route path="/messages"   element={<MessagesPage />} />
          <Route path="/tasks"      element={<TasksPage />} />
          <Route path="/schedule"   element={<SchedulePage />} />
          <Route path="/analytics"  element={<AnalyticsPage />} />
          <Route path="/commands"   element={<CommandPage />} />
          <Route path="/settings"   element={<SettingsPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
