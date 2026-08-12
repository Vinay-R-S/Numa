"use client"

import type { RefObject } from "react"
import { Bot, Send, Square, X, Zap } from "lucide-react"

import { AgentMessageContent } from "@/components/agents/AgentMessageContent"
import { Button } from "@/components/ui/button"
import { HEALTH_AGENT_SUGGESTIONS } from "../health.constants"
import type { HealthAgentMessage } from "../health.types"

function ChatBubble({ message }: { message: HealthAgentMessage }) {
  const isUser = message.role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <Bot className="h-3.5 w-3.5 text-primary" />
        </div>
      )}
      <div
        className={`min-w-0 max-w-[85%] overflow-hidden rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-primary/15 text-foreground rounded-br-sm"
            : "bg-muted/50 text-foreground rounded-bl-sm"
        }`}
      >
        <AgentMessageContent content={message.content} />
      </div>
    </div>
  )
}

interface HealthAgentPanelProps {
  messages: HealthAgentMessage[]
  input: string
  sending: boolean
  canSend: boolean
  error: string | null
  endRef: RefObject<HTMLDivElement | null>
  onInputChange: (value: string) => void
  onSend: () => void
  onStop: () => void
  onSelectSuggestion: (query: string) => void
  onClose: () => void
}

export function HealthAgentPanel({
  messages,
  input,
  sending,
  canSend,
  error,
  endRef,
  onInputChange,
  onSend,
  onStop,
  onSelectSuggestion,
  onClose,
}: HealthAgentPanelProps) {
  return (
    <section className="fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:bottom-6 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4">

      {/* Chat header */}
      <div className="flex items-center gap-2 border-b border-border/40 px-1 pb-3 shrink-0">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
          <Zap className="h-3.5 w-3.5 text-primary" />
        </div>
        <span className="text-sm font-semibold text-foreground">Health Agent</span>
        <span className="ml-auto rounded-full border border-border/30 bg-background/40 px-2 py-0.5 text-[10px] text-muted-foreground">
          Groq &bull; LangGraph
        </span>
        <button
          type="button"
          onClick={onClose}
          className="ml-1 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Quick actions */}
      <div className="border-b border-border/20 px-1 py-2 shrink-0">
        <div className="flex flex-wrap gap-1.5">
          {HEALTH_AGENT_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => onSelectSuggestion(suggestion)}
              className="rounded-full border border-border/40 bg-background/40 px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-foreground"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 px-1 py-3 min-h-0">
        {messages.map((message, index) => (
          <ChatBubble key={`${message.role}-${index}`} message={message} />
        ))}

        {sending && (
          <div className="flex items-start gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
              <Bot className="h-3.5 w-3.5 text-primary" />
            </div>
            <div className="rounded-2xl rounded-bl-sm bg-muted/50 px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
                </div>
                <span className="text-xs text-muted-foreground">Thinking and generating output...</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">{error}</p>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border/40 px-1 pt-3 shrink-0">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                onSend()
              }
            }}
            placeholder="Ask the Health agent..."
            disabled={sending}
            className="flex-1 rounded-xl border border-border/40 bg-background px-3.5 py-2 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-50"
          />
          <Button
            type="button"
            size="sm"
            variant={sending ? "destructive" : "default"}
            onClick={() => (sending ? onStop() : onSend())}
            disabled={!canSend && !sending}
            className="shrink-0"
          >
            {sending ? <Square className="h-4 w-4 sm:mr-1" /> : <Send className="h-4 w-4 sm:mr-1" />}
            <span className="hidden sm:inline">{sending ? "Stop" : "Send"}</span>
          </Button>
        </div>
      </div>
    </section>
  )
}
