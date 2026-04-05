/**
 * Analytics page — weekly/monthly graphs using Recharts.
 */
import { useState, useEffect } from 'react'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import api from '../lib/api'
import { Spinner, StatCard } from '../components/ui'
import TopBar from '../components/TopBar'
import { TrendingUp, CheckSquare, MessageSquare, Zap, Clock } from 'lucide-react'

const CUSTOM_TOOLTIP = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-3 text-xs space-y-1 shadow-xl">
      <p className="text-gray-400 font-medium mb-1.5">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-300">{p.name}:</span>
          <span className="font-semibold text-white">{p.value}</span>
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const [period,  setPeriod]  = useState('week')
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.get(`/analytics/${period}`)
      .then(({ data }) => setData(data))
      .finally(() => setLoading(false))
  }, [period])

  const rows   = data?.data || []
  const totals = data?.totals || {}

  const chartData = rows.map((r) => ({
    day: format(parseISO(r.period_date), period === 'week' ? 'EEE' : 'MMM d'),
    Tasks:       r.tasks_completed,
    Messages:    r.messages_sent,
    Commands:    r.commands_used,
    Focus:       Math.round((r.focus_minutes || 0) / 60 * 10) / 10,
    Score:       r.productivity_score,
  }))

  return (
    <>
      <TopBar title="Analytics" />
      <main className="p-6 space-y-6 animate-fade-slide-up">

        {/* Period toggle */}
        <div className="flex gap-2">
          {['week', 'month'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`btn-${period === p ? 'primary' : 'secondary'} text-xs py-1.5 capitalize`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Totals */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard icon={CheckSquare}   label="Tasks done"    value={totals.tasks_completed} color="text-emerald-400" />
          <StatCard icon={TrendingUp}    label="Tasks created" value={totals.tasks_created}   color="text-numa-400" />
          <StatCard icon={MessageSquare} label="Messages"      value={totals.messages_sent}   color="text-blue-400" />
          <StatCard icon={Zap}           label="Commands used" value={totals.commands_used}   color="text-purple-400" />
          <StatCard icon={Clock}         label="Focus hours"   value={Math.round((totals.focus_minutes || 0) / 60)} color="text-yellow-400" />
        </div>

        {loading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Tasks + Messages area chart */}
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-200 mb-4">Tasks & Messages</h3>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gTask" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gMsg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="day" tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CUSTOM_TOOLTIP />} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
                  <Area type="monotone" dataKey="Tasks"    stroke="#10b981" fill="url(#gTask)" strokeWidth={2} dot={false} />
                  <Area type="monotone" dataKey="Messages" stroke="#f59e0b" fill="url(#gMsg)"  strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Productivity score bar chart */}
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-200 mb-4">Productivity Score</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="day" tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CUSTOM_TOOLTIP />} />
                  <Bar dataKey="Score" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={32} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Commands usage bar chart */}
            <div className="card lg:col-span-2">
              <h3 className="text-sm font-semibold text-gray-200 mb-4">Daily Commands Used</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="day" tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#4b5563', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CUSTOM_TOOLTIP />} />
                  <Bar dataKey="Commands" fill="#a855f7" radius={[4, 4, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </main>
    </>
  )
}
