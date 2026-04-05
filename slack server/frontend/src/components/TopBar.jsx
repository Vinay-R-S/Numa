/**
 * Top navigation bar (shown inside authenticated layout).
 */
import { Bell, Search } from 'lucide-react'
import { useAuthStore }      from '../store/authStore'
import { useDashboardStore } from '../store/dashboardStore'

export default function TopBar({ title }) {
  const user        = useAuthStore((s) => s.user)
  const unread      = useDashboardStore((s) => s.data?.unread_nudges || 0)

  return (
    <header className="sticky top-0 z-30 bg-gray-950/80 backdrop-blur border-b border-gray-800/60
                       flex items-center gap-4 px-6 h-14">
      <h1 className="text-sm font-semibold text-gray-200 flex-1">{title}</h1>

      {/* Search hint */}
      <button className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-gray-800/70 border border-gray-700/50
                         rounded-lg text-xs text-gray-500 hover:text-gray-300 transition-colors w-48">
        <Search size={13} />
        Quick search…
        <kbd className="ml-auto font-mono text-[10px] border border-gray-700 rounded px-1 py-0.5">⌘K</kbd>
      </button>

      {/* Nudge bell */}
      <button className="relative btn-ghost p-2">
        <Bell size={16} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-numa-500
                           text-[10px] font-bold text-white flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
    </header>
  )
}
