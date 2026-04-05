/**
 * Login page — "Login with Slack" OAuth button.
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, MessageSquare, CheckSquare, BarChart2, ArrowRight } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const FEATURES = [
  { icon: MessageSquare, label: 'Slack messages in one view'              },
  { icon: CheckSquare,   label: 'Tasks from /numa commands in real-time'  },
  { icon: BarChart2,     label: 'Productivity analytics & mood tracking'  },
  { icon: Zap,           label: 'AI-generated daily plans'                },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true })
  }, [isAuthenticated])

  const handleSlackLogin = () => {
    window.location.href = `${API_BASE}/auth/slack`
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      {/* Background gradient blob */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2
                        w-96 h-96 bg-numa-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm animate-fade-slide-up">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-numa-500 to-purple-600
                          flex items-center justify-center mb-4 shadow-lg shadow-numa-500/20">
            <Zap size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Welcome to NUMA</h1>
          <p className="text-sm text-gray-500 mt-1.5 text-center">
            Your personal productivity layer on top of Slack
          </p>
        </div>

        {/* Card */}
        <div className="card space-y-6">
          {/* Feature list */}
          <ul className="space-y-3">
            {FEATURES.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-3 text-sm text-gray-400">
                <div className="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0">
                  <Icon size={14} className="text-numa-400" />
                </div>
                {label}
              </li>
            ))}
          </ul>

          {/* Slack login button */}
          <button
            onClick={handleSlackLogin}
            className="w-full flex items-center justify-center gap-3 py-3 px-4
                       bg-[#4A154B] hover:bg-[#3d1040] text-white rounded-xl font-semibold
                       text-sm transition-colors duration-150 shadow-lg"
          >
            {/* Slack logo SVG */}
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
              <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
            </svg>
            Continue with Slack
            <ArrowRight size={16} className="ml-auto" />
          </button>

          <p className="text-center text-[11px] text-gray-600">
            By continuing you agree to NUMA's Terms of Service.
          </p>
        </div>
      </div>
    </div>
  )
}
