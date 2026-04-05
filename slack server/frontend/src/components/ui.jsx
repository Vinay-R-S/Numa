import { clsx } from 'clsx'

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 20, className }) {
  return (
    <svg
      className={clsx('animate-spin text-numa-500', className)}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
    </svg>
  )
}

// ── Avatar ────────────────────────────────────────────────────────────────────
export function Avatar({ src, name = '?', size = 36 }) {
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        className="rounded-xl object-cover flex-shrink-0"
        style={{ width: size, height: size }}
      />
    )
  }
  return (
    <div
      className="rounded-xl bg-numa-900/60 border border-numa-800 flex items-center justify-center
                 text-numa-300 font-bold font-mono flex-shrink-0"
      style={{ width: size, height: size, fontSize: size * 0.35 }}
    >
      {initials}
    </div>
  )
}

// ── Status dot ────────────────────────────────────────────────────────────────
export function StatusDot({ online = true }) {
  return (
    <span className="relative inline-flex">
      <span
        className={clsx(
          'w-2 h-2 rounded-full',
          online ? 'bg-emerald-400' : 'bg-gray-600',
        )}
      />
      {online && (
        <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-40" />
      )}
    </span>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
      {Icon && (
        <div className="w-12 h-12 rounded-2xl bg-gray-800 flex items-center justify-center">
          <Icon size={22} className="text-gray-500" />
        </div>
      )}
      <div>
        <p className="text-sm font-medium text-gray-300">{title}</p>
        {description && <p className="text-xs text-gray-600 mt-1">{description}</p>}
      </div>
      {action}
    </div>
  )
}

// ── Section header ────────────────────────────────────────────────────────────
export function SectionHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="text-base font-semibold text-gray-100">{title}</h2>
        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────────────────────
export function StatCard({ icon: Icon, label, value, trend, color = 'text-numa-400' }) {
  return (
    <div className="card-sm flex items-center gap-4">
      <div className="w-10 h-10 rounded-xl bg-gray-800 flex items-center justify-center flex-shrink-0">
        <Icon size={18} className={color} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 truncate">{label}</p>
        <p className="text-xl font-bold text-gray-100 leading-tight">{value ?? '—'}</p>
        {trend !== undefined && (
          <p className={clsx('text-xs mt-0.5', trend >= 0 ? 'text-emerald-400' : 'text-red-400')}>
            {trend >= 0 ? '+' : ''}{trend}% vs last week
          </p>
        )}
      </div>
    </div>
  )
}

// ── Priority badge ────────────────────────────────────────────────────────────
const PRIORITY_CLASS = {
  urgent: 'badge-red',
  high:   'badge-yellow',
  medium: 'badge-blue',
  low:    'badge-gray',
}

export function PriorityBadge({ priority }) {
  return <span className={PRIORITY_CLASS[priority] || 'badge-gray'}>{priority}</span>
}

// ── Status badge ──────────────────────────────────────────────────────────────
const STATUS_CLASS = {
  todo:        'badge-gray',
  in_progress: 'badge-blue',
  done:        'badge-green',
  cancelled:   'badge-red',
}

export function StatusBadge({ status }) {
  return <span className={STATUS_CLASS[status] || 'badge-gray'}>{status?.replace('_', ' ')}</span>
}

// ── Mood emoji ────────────────────────────────────────────────────────────────
const MOOD_EMOJI = { great: '😄', good: '🙂', okay: '😐', low: '😕', bad: '😞' }
const MOOD_COLOR = {
  great: 'text-emerald-400',
  good:  'text-green-400',
  okay:  'text-yellow-400',
  low:   'text-orange-400',
  bad:   'text-red-400',
}

export function MoodDisplay({ mood }) {
  return (
    <span className={clsx('text-sm font-medium', MOOD_COLOR[mood] || 'text-gray-400')}>
      {MOOD_EMOJI[mood] || '—'} {mood}
    </span>
  )
}
