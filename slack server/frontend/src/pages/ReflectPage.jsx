/**
 * Reflection page — guided end-of-day journal with history.
 */
import { useState, useEffect } from 'react'
import { format, parseISO } from 'date-fns'
import api from '../lib/api'
import { Spinner, EmptyState, SectionHeader } from '../components/ui'
import TopBar from '../components/TopBar'
import { BookOpen, ThumbsUp, Lightbulb, Heart, Target, ChevronDown, ChevronUp } from 'lucide-react'

const FIELDS = [
  {
    key:         'what_went_well',
    label:       'What went well today?',
    placeholder: 'Celebrate your wins, big or small...',
    icon:        ThumbsUp,
    color:       'text-emerald-400',
  },
  {
    key:         'what_to_improve',
    label:       'What could be improved?',
    placeholder: 'Any blockers or things to do differently...',
    icon:        Lightbulb,
    color:       'text-yellow-400',
  },
  {
    key:         'gratitude',
    label:       'Gratitude',
    placeholder: 'Three things you\'re grateful for...',
    icon:        Heart,
    color:       'text-pink-400',
  },
  {
    key:         'tomorrow_focus',
    label:       'Tomorrow\'s focus',
    placeholder: 'Your #1 priority for tomorrow...',
    icon:        Target,
    color:       'text-numa-400',
  },
]

function ReflectionCard({ item }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-700/30 transition-colors"
      >
        <span className="text-sm font-medium text-gray-200">
          {format(parseISO(item.reflection_date), 'EEEE, MMMM d')}
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-700/50 pt-3">
          {FIELDS.map(({ key, label, icon: Icon, color }) =>
            item[key] ? (
              <div key={key}>
                <p className={`text-[10px] font-semibold uppercase tracking-wider mb-1 flex items-center gap-1.5 ${color}`}>
                  <Icon className="w-3 h-3" />{label}
                </p>
                <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{item[key]}</p>
              </div>
            ) : null
          )}
        </div>
      )}
    </div>
  )
}

export default function ReflectPage() {
  const [form,    setForm]    = useState({ what_went_well: '', what_to_improve: '', gratitude: '', tomorrow_focus: '' })
  const [saving,  setSaving]  = useState(false)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [flash,   setFlash]   = useState('')

  useEffect(() => {
    api.get('/reflect')
      .then(({ data }) => setHistory(data))
      .finally(() => setLoading(false))
  }, [])

  const updateField = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    const hasContent = Object.values(form).some((v) => v.trim())
    if (!hasContent) return
    setSaving(true)
    try {
      const { data } = await api.post('/reflect', {
        ...Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v.trim() || null])),
        reflection_date: new Date().toISOString().split('T')[0],
      })
      setHistory((h) => [data, ...h])
      setForm({ what_went_well: '', what_to_improve: '', gratitude: '', tomorrow_focus: '' })
      setFlash('Reflection saved!')
      setTimeout(() => setFlash(''), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <TopBar title="Reflect" />
      <main className="p-6 max-w-2xl space-y-6 animate-fade-slide-up">

        {flash && (
          <div className="bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-sm rounded-xl px-4 py-2.5">
            {flash}
          </div>
        )}

        {/* Form */}
        <div className="card">
          <SectionHeader
            title="End-of-Day Reflection"
            subtitle="A few minutes of reflection compounds over time"
          />
          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            {FIELDS.map(({ key, label, placeholder, icon: Icon, color }) => (
              <div key={key}>
                <label className={`text-xs font-medium mb-1.5 flex items-center gap-1.5 ${color}`}>
                  <Icon className="w-3.5 h-3.5" />{label}
                </label>
                <textarea
                  value={form[key]}
                  onChange={(e) => updateField(key, e.target.value)}
                  rows={3}
                  placeholder={placeholder}
                  className="input resize-none"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={saving || !Object.values(form).some((v) => v.trim())}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {saving ? <Spinner className="w-4 h-4" /> : <BookOpen className="w-4 h-4" />}
              Save Reflection
            </button>
          </form>
        </div>

        {/* History */}
        <div className="space-y-3">
          <SectionHeader title="Past Reflections" />
          {loading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : history.length === 0 ? (
            <div className="card">
              <EmptyState
                icon={BookOpen}
                title="No reflections yet"
                description="Your first reflection will appear here after you save it."
              />
            </div>
          ) : (
            <div className="space-y-2">
              {history.map((item) => <ReflectionCard key={item.id} item={item} />)}
            </div>
          )}
        </div>
      </main>
    </>
  )
}
