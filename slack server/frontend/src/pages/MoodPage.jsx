/**
 * Mood logging page — log energy/mood and view history.
 */
import { useState, useEffect } from 'react'
import { format, parseISO } from 'date-fns'
import api from '../lib/api'
import { Spinner, EmptyState, MoodDisplay, SectionHeader } from '../components/ui'
import TopBar from '../components/TopBar'
import { Smile, Frown, Zap, NotebookPen } from 'lucide-react'

const MOOD_OPTIONS = [
  { value: 'bad',   label: 'Bad',      icon: '😞', color: 'bg-red-500/15 border-red-500/40 text-red-400' },
  { value: 'low',   label: 'Low',      icon: '😕', color: 'bg-orange-500/15 border-orange-500/40 text-orange-400' },
  { value: 'okay',  label: 'Okay',     icon: '😐', color: 'bg-yellow-500/15 border-yellow-500/40 text-yellow-400' },
  { value: 'good',  label: 'Good',     icon: '🙂', color: 'bg-lime-500/15 border-lime-500/40 text-lime-400' },
  { value: 'great', label: 'Great',    icon: '😄', color: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400' },
]

export default function MoodPage() {
  const [mood,    setMood]    = useState(null)
  const [energy,  setEnergy]  = useState(5)
  const [note,    setNote]    = useState('')
  const [saving,  setSaving]  = useState(false)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [flash,   setFlash]   = useState('')

  useEffect(() => {
    api.get('/mood')
      .then(({ data }) => setHistory(data))
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!mood) return
    setSaving(true)
    try {
      const { data } = await api.post('/mood', {
        mood:   mood,
        energy: energy,
        note:   note.trim() || null,
      })
      setHistory((h) => [data, ...h])
      setMood(null)
      setEnergy(5)
      setNote('')
      setFlash('Mood logged!')
      setTimeout(() => setFlash(''), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <TopBar title="Mood" />
      <main className="p-6 max-w-2xl space-y-6 animate-fade-slide-up">

        {flash && (
          <div className="bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-sm rounded-xl px-4 py-2.5">
            {flash}
          </div>
        )}

        {/* Log form */}
        <div className="card space-y-5">
          <SectionHeader title="How are you feeling?" subtitle="Log your mood and energy level" />
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Mood picker */}
            <div>
              <p className="text-xs text-gray-500 mb-2.5">Mood</p>
              <div className="flex gap-2 flex-wrap">
                {MOOD_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setMood(opt.value)}
                    className={`flex flex-col items-center gap-1 px-4 py-3 rounded-xl border transition-all text-xs font-medium
                      ${mood === opt.value ? opt.color + ' scale-105 shadow-lg' : 'bg-gray-800/60 border-gray-700 text-gray-400 hover:bg-gray-700/60'}`}
                  >
                    <span className="text-2xl">{opt.icon}</span>
                    <span>{opt.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Energy slider */}
            <div>
              <label className="text-xs text-gray-500 mb-2 flex justify-between">
                <span className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" />Energy level</span>
                <span className="font-semibold text-numa-400">{energy} / 10</span>
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={energy}
                onChange={(e) => setEnergy(Number(e.target.value))}
                className="w-full accent-numa-500 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                <span>Low</span><span>High</span>
              </div>
            </div>

            {/* Optional note */}
            <div>
              <label className="text-xs text-gray-500 mb-1.5 flex items-center gap-1.5">
                <NotebookPen className="w-3.5 h-3.5" />Note <span className="text-gray-600">(optional)</span>
              </label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                placeholder="Any context for how you're feeling..."
                className="input resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={!mood || saving}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {saving ? <Spinner className="w-4 h-4" /> : <Smile className="w-4 h-4" />}
              Log Mood
            </button>
          </form>
        </div>

        {/* History */}
        <div className="card">
          <SectionHeader title="Mood History" />
          {loading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : history.length === 0 ? (
            <EmptyState icon={Frown} title="No mood logs yet" description="Start tracking how you feel each day." />
          ) : (
            <ul className="divide-y divide-gray-800">
              {history.map((item) => (
                <li key={item.id} className="py-3 flex items-start gap-4">
                  <MoodDisplay mood={item.mood} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-0.5">
                      <span className="text-xs font-medium text-gray-300">
                        {MOOD_OPTIONS.find(m => m.value === item.mood)?.label}
                      </span>
                      <span className="flex items-center gap-1 text-[10px] text-gray-500">
                        <Zap className="w-3 h-3" />{item.energy}/10
                      </span>
                      <span className="ml-auto text-[10px] text-gray-600">
                        {format(parseISO(item.logged_at), 'MMM d, HH:mm')}
                      </span>
                    </div>
                    {item.note && (
                      <p className="text-xs text-gray-500 truncate">{item.note}</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </>
  )
}
