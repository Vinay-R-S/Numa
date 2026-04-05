/**
 * Schedule page — view and edit daily time blocks.
 */
import { useState, useEffect } from 'react'
import { Calendar, Plus, Save } from 'lucide-react'
import { format } from 'date-fns'
import api from '../lib/api'
import { Spinner, EmptyState } from '../components/ui'
import TopBar from '../components/TopBar'

const TAGS = ['Focus', 'Meeting', 'Break', 'Collab', 'Admin']
const TAG_COLORS = {
  Focus:   'border-l-numa-500  bg-numa-900/30',
  Meeting: 'border-l-yellow-500 bg-yellow-900/20',
  Break:   'border-l-emerald-500 bg-emerald-900/20',
  Collab:  'border-l-purple-500 bg-purple-900/20',
  Admin:   'border-l-gray-500   bg-gray-800/40',
}

const EMPTY_BLOCK = { label: '', start_time: '09:00', end_time: '10:00', tag: 'Focus' }

export default function SchedulePage() {
  const [plan,    setPlan]    = useState(null)
  const [blocks,  setBlocks]  = useState([])
  const [loading, setLoading] = useState(true)
  const [saving,  setSaving]  = useState(false)
  const today = format(new Date(), 'yyyy-MM-dd')

  useEffect(() => {
    api.get('/schedule/today').then(({ data }) => {
      if (data) {
        setPlan(data)
        setBlocks(data.blocks || [])
      }
    }).finally(() => setLoading(false))
  }, [])

  const addBlock = () => setBlocks((b) => [...b, { ...EMPTY_BLOCK }])

  const updateBlock = (i, field, value) =>
    setBlocks((b) => b.map((blk, idx) => idx === i ? { ...blk, [field]: value } : blk))

  const removeBlock = (i) => setBlocks((b) => b.filter((_, idx) => idx !== i))

  const save = async () => {
    setSaving(true)
    try {
      const { data } = await api.post('/schedule/plan', {
        plan_date: today,
        blocks: blocks.filter((b) => b.label.trim()),
      })
      setPlan(data)
      setBlocks(data.blocks || [])
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <TopBar title="Schedule" />
      <main className="p-6 space-y-6 animate-fade-slide-up">

        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-100">
              {format(new Date(), 'EEEE, MMMM d')}
            </h2>
            <p className="text-xs text-gray-500">Edit your daily time blocks</p>
          </div>
          <div className="flex gap-2">
            <button onClick={addBlock} className="btn-secondary text-xs py-1.5">
              <Plus size={13} /> Add Block
            </button>
            <button onClick={save} disabled={saving} className="btn-primary text-xs py-1.5">
              {saving ? <Spinner size={13} /> : <Save size={13} />}
              Save Plan
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : blocks.length === 0 ? (
          <div className="card">
            <EmptyState
              icon={Calendar}
              title="No schedule yet"
              description='Use /numa plan today in Slack or add blocks manually'
              action={<button onClick={addBlock} className="btn-primary text-sm"><Plus size={14} /> Add first block</button>}
            />
          </div>
        ) : (
          <div className="space-y-3">
            {blocks.map((block, i) => (
              <div key={i}
                   className={`border-l-[3px] rounded-r-xl px-4 py-3 ${TAG_COLORS[block.tag] || 'border-l-gray-600 bg-gray-800/40'}`}>
                <div className="flex items-center gap-3 flex-wrap">
                  <input
                    className="input flex-1 min-w-40 text-sm font-medium bg-transparent border-0 border-b border-gray-700 rounded-none px-0 focus:ring-0"
                    placeholder="Block label…"
                    value={block.label}
                    onChange={(e) => updateBlock(i, 'label', e.target.value)}
                  />
                  <input
                    type="time"
                    className="input w-28 text-sm font-mono"
                    value={block.start_time}
                    onChange={(e) => updateBlock(i, 'start_time', e.target.value)}
                  />
                  <span className="text-gray-600 text-sm">–</span>
                  <input
                    type="time"
                    className="input w-28 text-sm font-mono"
                    value={block.end_time}
                    onChange={(e) => updateBlock(i, 'end_time', e.target.value)}
                  />
                  <select
                    className="input w-28 text-sm"
                    value={block.tag}
                    onChange={(e) => updateBlock(i, 'tag', e.target.value)}
                  >
                    {TAGS.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <button
                    onClick={() => removeBlock(i)}
                    className="text-gray-700 hover:text-red-400 transition-colors"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

      </main>
    </>
  )
}
