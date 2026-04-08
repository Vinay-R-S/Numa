/**
 * Dashboard — today's full overview.
 */
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { CheckSquare, Clock, Zap, MessageSquare, TrendingUp } from 'lucide-react'
import { format } from 'date-fns'
import { useDashboardStore } from '../store/dashboardStore'
import { useTaskStore }      from '../store/taskStore'
import { StatCard, PriorityBadge, Spinner, EmptyState, SectionHeader } from '../components/ui'
import TopBar from '../components/TopBar'

// ── Productivity score ring ────────────────────────────────────────────────────
function ScoreRing({ score }) {
  const pct = score ?? 0
  const r   = 36
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={96} height={96} viewBox="0 0 96 96">
        <circle cx={48} cy={48} r={r} fill="none" stroke="#1f2937" strokeWidth={8} />
        <circle
          cx={48} cy={48} r={r} fill="none"
          stroke="url(#scoreGrad)" strokeWidth={8}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          transform="rotate(-90 48 48)"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <defs>
          <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#6366f1" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
        </defs>
        <text x={48} y={48} textAnchor="middle" dominantBaseline="middle"
              fill="white" fontSize={20} fontWeight={700} fontFamily="Inter">
          {score !== null && score !== undefined ? score : '—'}
        </text>
      </svg>
      <span className="text-xs text-gray-500">Today's score</span>
    </div>
  )
}

// ── Time block cards ──────────────────────────────────────────────────────────
const TAG_COLORS = {
  Focus:   'border-l-numa-500 bg-numa-900/20',
  Meeting: 'border-l-yellow-500 bg-yellow-900/10',
  Break:   'border-l-emerald-500 bg-emerald-900/10',
  Collab:  'border-l-purple-500 bg-purple-900/10',
}

function TimeBlock({ block }) {
  return (
    <div className={`border-l-2 rounded-r-lg px-3 py-2 ${TAG_COLORS[block.tag] || 'border-l-gray-600 bg-gray-800/40'}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-200">{block.label}</span>
        <span className="text-xs text-gray-500 font-mono">{block.start_time}–{block.end_time}</span>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { data, loading, fetchToday }  = useDashboardStore()
  const { tasks, fetchTasks, updateTask } = useTaskStore()

  useEffect(() => {
    fetchToday()
    fetchTasks()
  }, [])

  const todayTasks = data?.tasks_today || tasks.filter(
    (t) => t.status !== 'done' && t.status !== 'cancelled'
  ).slice(0, 6)

  if (loading && !data) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Spinner size={28} />
      </div>
    )
  }

  const plan   = data?.plan_today
  const blocks = plan?.blocks || []

  return (
    <>
      <TopBar title={`Good ${greeting()}, ${data?.user?.display_name?.split(' ')[0] || 'there'} 👋`} />

      <main className="p-6 space-y-6 animate-fade-slide-up">
        {/* ── Stat row ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={CheckSquare}  label="Tasks today"     value={todayTasks.length}         color="text-numa-400" />
          <StatCard icon={TrendingUp}   label="Completed"       value={data?.tasks_completed_today ?? 0} color="text-emerald-400" />
          <StatCard icon={MessageSquare} label="Messages"       value={data?.recent_messages?.length ?? 0} color="text-blue-400" />
          <StatCard icon={Zap}          label="Unread nudges"   value={data?.unread_nudges ?? 0} color="text-yellow-400" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ── Tasks ──────────────────────────────────────────────────── */}
          <div className="lg:col-span-2 card">
            <SectionHeader
              title="Tasks"
              subtitle={format(new Date(), 'EEEE, MMMM d')}
              action={
                <Link to="/tasks" className="btn-ghost text-xs">View all →</Link>
              }
            />

            {todayTasks.length === 0 ? (
              <EmptyState icon={CheckSquare} title="No tasks yet" description="Use /numa task add in Slack or add one directly" />
            ) : (
              <ul className="space-y-2 stagger">
                {todayTasks.map((task) => (
                  <li key={task.id}
                      className="flex items-center gap-3 py-2.5 border-b border-gray-800/50 last:border-0">
                    <button
                      onClick={() => updateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' })}
                      className={`w-5 h-5 rounded-full border flex-shrink-0 transition-colors
                        ${task.status === 'done' ? 'bg-emerald-500 border-emerald-500' : 'border-gray-600 hover:border-numa-500'}`}
                    />
                    <span className={`flex-1 text-sm ${task.status === 'done' ? 'line-through text-gray-600' : 'text-gray-200'}`}>
                      {task.title}
                    </span>
                    <PriorityBadge priority={task.priority} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* ── Today's plan + score ────────────────────────────────────── */}
          <div className="space-y-6">
            <div className="card flex flex-col items-center gap-4">
              <ScoreRing score={data?.productivity_score} />
            </div>

            <div className="card">
              <SectionHeader
                title="Today's Plan"
                subtitle={plan ? 'AI generated' : 'No plan yet'}
                action={<Link to="/schedule" className="btn-ghost text-xs">Edit →</Link>}
              />
              {blocks.length === 0 ? (
                <EmptyState icon={Clock} title="No plan" description="Use /numa plan today in Slack" />
              ) : (
                <div className="space-y-2 stagger">
                  {blocks.map((b, i) => <TimeBlock key={i} block={b} />)}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Recent Slack messages ────────────────────────────────────── */}
        <div className="card">
          <SectionHeader
            title="Recent Slack Messages"
            action={<Link to="/messages" className="btn-ghost text-xs">View all →</Link>}
          />
          {(!data?.recent_messages || data.recent_messages.length === 0) ? (
            <EmptyState icon={MessageSquare} title="No messages" description="Messages from Slack will appear here" />
          ) : (
            <ul className="divide-y divide-gray-800/50">
              {data.recent_messages.slice(0, 5).map((msg) => (
                <li key={msg.id} className="py-3 flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0 text-xs font-mono text-gray-400">
                    #
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-500 mb-0.5">{msg.channel_name || msg.channel_id}</p>
                    <p className="text-sm text-gray-300 truncate">{msg.text}</p>
                  </div>
                  <span className="text-[11px] text-gray-600 flex-shrink-0">
                    {msg.created_at ? format(new Date(msg.created_at), 'HH:mm') : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </>
  )
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}
