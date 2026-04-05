import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, CheckSquare,
  BarChart2, Settings, LogOut, Zap, Terminal,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useAuthStore } from '../store/authStore'
import { Avatar, StatusDot } from './ui'

const NAV = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/messages',   icon: MessageSquare,   label: 'Messages'  },
  { to: '/tasks',      icon: CheckSquare,     label: 'Tasks'     },
  { to: '/analytics',  icon: BarChart2,       label: 'Analytics' },
  { to: '/commands',   icon: Terminal,        label: 'Commands'  },
]

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="fixed left-0 top-0 h-full w-60 bg-gray-950 border-r border-gray-800/60
                      flex flex-col z-40">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-numa-500 to-purple-600
                          flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="font-bold text-white text-base tracking-tight">NUMA</span>
          <span className="ml-auto">
            <StatusDot online />
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150',
                isActive
                  ? 'bg-numa-900/60 text-numa-300 border border-numa-800/60'
                  : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/70',
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Settings + User */}
      <div className="px-3 py-4 border-t border-gray-800/60 space-y-1">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              isActive ? 'bg-numa-900/60 text-numa-300' : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/70',
            )
          }
        >
          <Settings size={16} />
          Settings
        </NavLink>

        {/* User profile */}
        <div className="flex items-center gap-3 px-3 py-2.5 mt-2">
          <Avatar src={user?.avatar_url} name={user?.display_name || 'You'} size={30} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-300 truncate">
              {user?.display_name || user?.real_name || 'You'}
            </p>
            <p className="text-[10px] text-gray-600 truncate">{user?.email || ''}</p>
          </div>
          <button
            onClick={handleLogout}
            className="text-gray-600 hover:text-red-400 transition-colors"
            title="Sign out"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  )
}
