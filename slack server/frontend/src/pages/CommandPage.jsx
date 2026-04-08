/**
 * CommandPage — natural-language Slack command console.
 * Users type plain English; the backend parses intent via Groq LLM
 * and executes the corresponding Slack / NUMA action.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Terminal, Zap, ChevronRight, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import api from '../lib/api'
import { Spinner } from '../components/ui'
import TopBar from '../components/TopBar'

// ── Intent metadata ──────────────────────────────────────────────────────────

const INTENT_META = {
  send_message:     { label: 'send message',     color: 'bg-blue-900/50 text-blue-300 border-blue-800/60' },
  schedule_message: { label: 'schedule message', color: 'bg-orange-900/50 text-orange-300 border-orange-800/60' },
  get_history:      { label: 'get history',      color: 'bg-cyan-900/50 text-cyan-300 border-cyan-800/60' },
  create_channel:   { label: 'create channel',   color: 'bg-purple-900/50 text-purple-300 border-purple-800/60' },
  rename_channel:   { label: 'rename channel',   color: 'bg-violet-900/50 text-violet-300 border-violet-800/60' },
  archive_channel:  { label: 'archive channel',  color: 'bg-gray-700/50 text-gray-400 border-gray-600/60' },
  invite_user:      { label: 'invite user',      color: 'bg-teal-900/50 text-teal-300 border-teal-800/60' },
  remove_user:      { label: 'remove user',      color: 'bg-red-900/50 text-red-300 border-red-800/60' },
  list_channels:    { label: 'list channels',    color: 'bg-indigo-900/50 text-indigo-300 border-indigo-800/60' },
  list_users:       { label: 'list users',       color: 'bg-indigo-900/50 text-indigo-300 border-indigo-800/60' },
  add_reaction:     { label: 'add reaction',     color: 'bg-yellow-900/50 text-yellow-300 border-yellow-800/60' },
  remove_reaction:  { label: 'remove reaction',  color: 'bg-yellow-900/50 text-yellow-400 border-yellow-800/60' },
  upload_file:      { label: 'upload file',      color: 'bg-sky-900/50 text-sky-300 border-sky-800/60' },
  task_add:         { label: 'add task',         color: 'bg-emerald-900/50 text-emerald-300 border-emerald-800/60' },
  task_list:        { label: 'list tasks',       color: 'bg-emerald-900/50 text-emerald-400 border-emerald-800/60' },
  plan_today:       { label: 'plan today',       color: 'bg-numa-900/50 text-numa-300 border-numa-800/60' },
  score:            { label: 'score',            color: 'bg-amber-900/50 text-amber-300 border-amber-800/60' },
  schedule_view:    { label: 'schedule view',    color: 'bg-amber-900/50 text-amber-400 border-amber-800/60' },
  unknown:          { label: 'unknown',          color: 'bg-red-900/50 text-red-400 border-red-800/60' },
}

function IntentBadge({ intent }) {
  const meta = INTENT_META[intent] || INTENT_META.unknown
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border',
      meta.color,
    )}>
      <Zap size={8} />
      {meta.label}
    </span>
  )
}

// ── Quick-command suggestion chips ───────────────────────────────────────────

const SUGGESTIONS = [
  'List all channels',
  'List workspace users',
  'What are my open tasks?',
  'Show today\'s plan',
  'What\'s my score today?',
  'Send "Hello team!" to #general',
  'Add task: Review pull request',
  'Create channel #new-project',
]

// ── Message bubbles ───────────────────────────────────────────────────────────

function UserBubble({ text }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[75%] bg-numa-600/20 border border-numa-700/40 rounded-2xl rounded-tr-sm
                      px-4 py-2.5 text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
        {text}
      </div>
    </div>
  )
}

function NUMABubble({ response, intent, error }) {
  return (
    <div className="flex justify-start gap-2.5">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-numa-500 to-purple-600
                      flex items-center justify-center flex-shrink-0 mt-0.5">
        <Zap size={13} className="text-white" />
      </div>

      <div className="max-w-[75%] space-y-1.5">
        {/* Response text */}
        <div className={clsx(
          'rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
          error
            ? 'bg-red-900/20 border border-red-800/40 text-red-300'
            : 'bg-gray-800/70 border border-gray-700/50 text-gray-200',
        )}>
          {response}
        </div>

        {/* Intent badge */}
        {intent && <IntentBadge intent={intent} />}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start gap-2.5">
      <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-numa-500 to-purple-600
                      flex items-center justify-center flex-shrink-0">
        <Zap size={13} className="text-white" />
      </div>
      <div className="bg-gray-800/70 border border-gray-700/50 rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CommandPage() {
  const [messages, setMessages] = useState([])
  const [input,    setInput]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Focus input on mount
  useEffect(() => { inputRef.current?.focus() }, [])

  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: trimmed, id: Date.now() }])
    setLoading(true)

    try {
      const { data } = await api.post('/chat', { message: trimmed })
      setMessages((prev) => [...prev, {
        role: 'numa',
        id: Date.now(),
        response: data.response,
        intent:   data.intent,
        error:    false,
      }])
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message || 'Something went wrong.'
      setMessages((prev) => [...prev, {
        role:     'numa',
        id:       Date.now(),
        response: errMsg,
        intent:   'unknown',
        error:    true,
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }, [loading])

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const clearHistory = () => setMessages([])

  return (
    <>
      <TopBar title="Commands" />

      <main className="flex flex-col h-[calc(100vh-57px)] animate-fade-slide-up">

        {/* ── Empty / welcome state ─────────────────────────────────────────── */}
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center gap-6 p-6">
            {/* Hero */}
            <div className="flex flex-col items-center gap-3 text-center">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-numa-500 to-purple-600
                              flex items-center justify-center shadow-lg shadow-numa-900/40">
                <Terminal size={26} className="text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-100">Slack Command Console</h2>
                <p className="text-sm text-gray-500 mt-1 max-w-sm">
                  Type any plain English instruction — NUMA understands your intent
                  and executes the action in Slack instantly.
                </p>
              </div>
            </div>

            {/* Suggestion chips */}
            <div className="flex flex-wrap gap-2 justify-center max-w-xl">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
                             bg-gray-800/60 border border-gray-700/50 text-gray-400
                             hover:bg-gray-700/60 hover:text-gray-200 hover:border-gray-600
                             transition-colors"
                >
                  <ChevronRight size={11} className="text-numa-500" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Message history ───────────────────────────────────────────────── */}
        {messages.length > 0 && (
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {messages.map((msg) =>
              msg.role === 'user'
                ? <UserBubble key={msg.id} text={msg.text} />
                : <NUMABubble key={msg.id} response={msg.response} intent={msg.intent} error={msg.error} />
            )}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}

        {/* ── Input bar ─────────────────────────────────────────────────────── */}
        <div className="flex-shrink-0 px-6 py-4 border-t border-gray-800/60 bg-gray-950/80 backdrop-blur">
          {/* Quick suggestion chips (persistent below existing messages) */}
          {messages.length > 0 && (
            <div className="flex gap-2 flex-wrap mb-3">
              {SUGGESTIONS.slice(0, 5).map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px]
                             bg-gray-800/50 border border-gray-700/40 text-gray-500
                             hover:text-gray-300 hover:border-gray-600 transition-colors"
                >
                  <ChevronRight size={9} className="text-numa-500" />
                  {s}
                </button>
              ))}
              <button
                onClick={clearHistory}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px]
                           bg-gray-800/50 border border-gray-700/40 text-gray-600
                           hover:text-red-400 hover:border-red-900/40 transition-colors ml-auto"
              >
                <Trash2 size={9} />
                clear
              </button>
            </div>
          )}

          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder='Try "Send hello to #general" or "Add task: Review PR"…'
              disabled={loading}
              className="flex-1 input text-sm resize-none min-h-[42px] max-h-32 py-2.5
                         disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed"
              style={{ height: 'auto' }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = `${Math.min(e.target.scrollHeight, 128)}px`
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              className="btn-primary h-[42px] px-4 flex-shrink-0 disabled:opacity-40
                         disabled:cursor-not-allowed"
            >
              {loading
                ? <Spinner size={16} />
                : <Send size={15} />
              }
            </button>
          </div>

          <p className="text-[10px] text-gray-700 mt-2 text-center">
            Press <kbd className="text-gray-500 bg-gray-800 px-1 py-0.5 rounded text-[10px]">Enter</kbd> to send
            · <kbd className="text-gray-500 bg-gray-800 px-1 py-0.5 rounded text-[10px]">Shift + Enter</kbd> for new line
          </p>
        </div>
      </main>
    </>
  )
}
