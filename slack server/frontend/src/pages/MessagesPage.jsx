/**
 * Messages page — Slack messages inside NUMA.
 * "My Messages" shows messages sent by the user.
 * "For Me" shows messages that mention the user or are @channel / @here broadcasts.
 *  Any actionable "For Me" message is auto-processed by the NUMA agent to create tasks.
 */
import { useState, useEffect } from 'react'
import { MessageSquare, Hash, RefreshCw, AtSign, Megaphone, Bot } from 'lucide-react'
import { format } from 'date-fns'
import api from '../lib/api'
import { useAuthStore } from '../store/authStore'
import { Spinner, EmptyState } from '../components/ui'
import TopBar from '../components/TopBar'

// Detect what kind of relevance a message has for the viewer
function getRelevanceType(text, slackUserId) {
  const isDirect   = slackUserId && text.includes(`<@${slackUserId}>`)
  const isBroadcast = text.includes('<!channel>') || text.includes('<!here>') || text.includes('<!everyone>')
  return { isDirect, isBroadcast }
}

// Strip / prettify Slack mrkdwn tokens for display
function formatText(text) {
  return text
    .replace(/<@([A-Z0-9]+)>/g, '@user')   // replace user mentions
    .replace(/<!channel>/g, '@channel')
    .replace(/<!here>/g,    '@here')
    .replace(/<!everyone>/g,'@everyone')
    .replace(/<#[A-Z0-9]+\|([^>]+)>/g, '#$1') // channel links
    .replace(/<([^|>]+)\|([^>]+)>/g, '$2')     // labelled URLs
    .replace(/<([^>]+)>/g, '$1')               // bare URLs
}

export default function MessagesPage() {
  const user = useAuthStore((s) => s.user)

  const [view,     setView]     = useState('mine')   // 'mine' | 'forme'
  const [messages, setMessages] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [channel,  setChannel]  = useState('')
  const [channels, setChannels] = useState([])

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (channel)          params.channel_id    = channel
      if (view === 'forme') params.relevant_only = true

      const { data } = await api.get('/messages', { params })
      setMessages(data)

      // Derive channel list from first load
      if (!channel) {
        const seen = new Map()
        data.forEach((m) => {
          if (m.channel_id && !seen.has(m.channel_id))
            seen.set(m.channel_id, m.channel_name || m.channel_id)
        })
        setChannels([...seen.entries()])
      }
    } finally {
      setLoading(false)
    }
  }

  // Reload when view or channel changes
  useEffect(() => {
    setChannel('') // reset channel filter on view switch
  }, [view])

  useEffect(() => {
    load()
    const id = window.setInterval(load, 10_000)
    return () => window.clearInterval(id)
  }, [view, channel])

  return (
    <>
      <TopBar title="Messages" />
      <main className="p-6 space-y-4 animate-fade-slide-up">

        {/* View toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setView('mine')}
            className={`btn-${view === 'mine' ? 'primary' : 'secondary'} text-xs py-1.5 flex items-center gap-1.5`}
          >
            <MessageSquare size={13} />
            My Messages
          </button>
          <button
            onClick={() => setView('forme')}
            className={`btn-${view === 'forme' ? 'primary' : 'secondary'} text-xs py-1.5 flex items-center gap-1.5`}
          >
            <AtSign size={13} />
            For Me
          </button>

          <button onClick={load} className="btn-ghost ml-auto text-xs py-1.5">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Agent info banner — only on "For Me" view */}
        {view === 'forme' && (
          <div className="flex items-start gap-2.5 rounded-xl bg-numa-500/10 border border-numa-500/20 px-4 py-3">
            <Bot size={15} className="text-numa-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-gray-400 leading-relaxed">
              Showing messages that mention you or broadcast to @channel / @here.
              The NUMA agent automatically analyses these and creates tasks for any action items it detects.
            </p>
          </div>
        )}

        {/* Channel filter */}
        {channels.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setChannel('')}
              className={`btn-${channel === '' ? 'primary' : 'secondary'} text-xs py-1.5`}
            >
              All channels
            </button>
            {channels.map(([id, name]) => (
              <button
                key={id}
                onClick={() => setChannel(id)}
                className={`btn-${channel === id ? 'primary' : 'secondary'} text-xs py-1.5 flex items-center gap-1`}
              >
                <Hash size={11} />
                {name}
              </button>
            ))}
          </div>
        )}

        {/* Message list */}
        <div className="card divide-y divide-gray-800/50">
          {loading ? (
            <div className="py-16 flex justify-center"><Spinner /></div>
          ) : messages.length === 0 ? (
            <EmptyState
              icon={view === 'forme' ? AtSign : MessageSquare}
              title={view === 'forme' ? 'No messages for you yet' : 'No messages found'}
              description={
                view === 'forme'
                  ? 'Messages that mention you or use @channel / @here will appear here'
                  : 'Messages sent on Slack will sync here automatically'
              }
            />
          ) : (
            messages.map((msg) => {
              const { isDirect, isBroadcast } = getRelevanceType(
                msg.text || '',
                user?.slack_user_id,
              )
              return (
                <div
                  key={msg.id}
                  className="py-3.5 flex items-start gap-3 hover:bg-gray-800/20 px-2 rounded-lg transition-colors"
                >
                  {/* Icon */}
                  <div className="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0 text-xs text-gray-500 font-mono">
                    {msg.thread_ts ? '↩' : '#'}
                  </div>

                  {/* Body */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-medium text-numa-400">
                        #{msg.channel_name || msg.channel_id}
                      </span>

                      {/* Relevance badges (only shown in "For Me" view) */}
                      {view === 'forme' && isDirect && (
                        <span className="inline-flex items-center gap-1 badge-purple text-[10px]">
                          <AtSign size={9} />
                          mentioned you
                        </span>
                      )}
                      {view === 'forme' && isBroadcast && (
                        <span className="inline-flex items-center gap-1 badge-yellow text-[10px]">
                          <Megaphone size={9} />
                          broadcast
                        </span>
                      )}

                      {msg.message_type !== 'message' && (
                        <span className="badge-purple text-[10px]">{msg.message_type}</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-300 whitespace-pre-line break-words">
                      {formatText(msg.text || '')}
                    </p>
                  </div>

                  {/* Timestamp */}
                  <span className="text-[11px] text-gray-600 flex-shrink-0 pt-0.5">
                    {msg.created_at ? format(new Date(msg.created_at), 'MMM d, HH:mm') : ''}
                  </span>
                </div>
              )
            })
          )}
        </div>
      </main>
    </>
  )
}
