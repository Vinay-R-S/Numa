/**
 * Tasks page — full task management with filters and inline status toggle.
 */
import { useState, useEffect } from 'react'
import { Plus, Trash2, CheckSquare } from 'lucide-react'
import { useTaskStore } from '../store/taskStore'
import { Spinner, EmptyState, PriorityBadge, StatusBadge } from '../components/ui'
import TopBar from '../components/TopBar'

const STATUSES = ['all', 'todo', 'in_progress', 'done']
const PRIORITIES = ['low', 'medium', 'high', 'urgent']

function AddTaskModal({ onClose, onAdd }) {
  const [title,    setTitle]    = useState('')
  const [priority, setPriority] = useState('medium')
  const [dueDate,  setDueDate]  = useState('')
  const [saving,   setSaving]   = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      await onAdd({ title: title.trim(), priority, due_date: dueDate || null })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="card w-full max-w-md animate-fade-slide-up">
        <h3 className="text-base font-semibold text-gray-100 mb-4">Add Task</h3>
        <form onSubmit={submit} className="space-y-4">
          <input
            className="input"
            placeholder="Task title…"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Priority</label>
              <select
                className="input text-sm"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              >
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Due date</label>
              <input
                type="date"
                className="input text-sm"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? <Spinner size={14} /> : <Plus size={14} />}
              Add Task
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function TasksPage() {
  const { tasks, loading, fetchTasks, addTask, updateTask, deleteTask } = useTaskStore()
  const [statusFilter, setStatusFilter] = useState('all')
  const [showModal,    setShowModal]    = useState(false)

  useEffect(() => { fetchTasks() }, [])

  const filtered = statusFilter === 'all'
    ? tasks
    : tasks.filter((t) => t.status === statusFilter)

  return (
    <>
      <TopBar title="Tasks" />
      <main className="p-6 space-y-4 animate-fade-slide-up">

        {/* Filters + add */}
        <div className="flex items-center gap-2 flex-wrap">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`btn-${statusFilter === s ? 'primary' : 'secondary'} text-xs py-1.5 capitalize`}
            >
              {s === 'all' ? 'All' : s.replace('_', ' ')}
            </button>
          ))}
          <button onClick={() => setShowModal(true)} className="btn-primary text-xs py-1.5 ml-auto">
            <Plus size={13} /> New Task
          </button>
        </div>

        {/* Task list */}
        <div className="card divide-y divide-gray-800/50">
          {loading ? (
            <div className="py-16 flex justify-center"><Spinner /></div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={CheckSquare}
              title="No tasks"
              description='Use /numa task add "task name" in Slack or click New Task'
              action={
                <button onClick={() => setShowModal(true)} className="btn-primary text-sm">
                  <Plus size={14} /> Add task
                </button>
              }
            />
          ) : (
            filtered.map((task) => (
              <div key={task.id}
                   className="flex items-center gap-3 py-3 hover:bg-gray-800/20 px-1 rounded-lg transition-colors">
                {/* Toggle done */}
                <button
                  onClick={() => updateTask(task.id, {
                    status: task.status === 'done' ? 'todo' : 'done',
                  })}
                  className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors
                    ${task.status === 'done'
                      ? 'bg-emerald-500 border-emerald-500'
                      : 'border-gray-600 hover:border-numa-500'}`}
                >
                  {task.status === 'done' && (
                    <svg viewBox="0 0 10 10" className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="2,5 4,7 8,3" />
                    </svg>
                  )}
                </button>

                {/* Title */}
                <span className={`flex-1 text-sm ${task.status === 'done' ? 'line-through text-gray-600' : 'text-gray-200'}`}>
                  {task.title}
                </span>

                {/* Meta */}
                <div className="flex items-center gap-2">
                  <PriorityBadge priority={task.priority} />
                  <StatusBadge   status={task.status} />
                  {task.source === 'slack' && (
                    <span className="badge-purple text-[10px]">Slack</span>
                  )}
                  {task.due_date && (
                    <span className="text-[11px] text-gray-600 font-mono">{task.due_date}</span>
                  )}
                </div>

                {/* Delete */}
                <button
                  onClick={() => deleteTask(task.id)}
                  className="text-gray-700 hover:text-red-400 transition-colors ml-1"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))
          )}
        </div>
      </main>

      {showModal && (
        <AddTaskModal onClose={() => setShowModal(false)} onAdd={addTask} />
      )}
    </>
  )
}
