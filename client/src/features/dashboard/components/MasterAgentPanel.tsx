"use client"

import { Bot, BrainCircuit, Loader2, Send, Square, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { AgentMessageContent } from "@/components/agents/AgentMessageContent"
import { cn } from "@/lib/utils"
import type { UseMasterAgentChatReturn } from "../useMasterAgentChat"

type MasterAgentPanelProps = Omit<UseMasterAgentChatReturn, "open" | "toggle">

export function MasterAgentPanel({
  messages,
  input,
  sending,
  chatError,
  lastDelegation,
  canSend,
  chatEndRef,
  setInput,
  close,
  handleSend,
  handleStop,
}: MasterAgentPanelProps) {
  return (
    <section className="fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:bottom-6 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
            <BrainCircuit className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">Master Agent</p>
            <p className="text-[10px] text-muted-foreground">
              {lastDelegation ? `Last: ${lastDelegation}` : "Ask anything"}
            </p>
          </div>
        </div>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={close}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="mb-3 min-h-0 flex-1 space-y-2 overflow-y-auto rounded-xl border border-border/30 bg-background/40 p-2 sm:p-3">
        {messages.map((msg, i) => (
          <div
            key={`${msg.role}-${i}`}
            className={cn(
              "min-w-0 max-w-[90%] overflow-hidden rounded-xl px-3 py-2 text-[13px] leading-relaxed",
              msg.role === "user"
                ? "ml-auto bg-primary/15 text-foreground"
                : "mr-auto bg-muted/50 text-foreground"
            )}
          >
            {msg.role === "assistant" && <Bot className="mr-1 inline h-3 w-3 text-primary" />}
            <AgentMessageContent content={msg.content} />
          </div>
        ))}
        {sending && (
          <div className="mr-auto flex items-center gap-1.5 rounded-xl bg-muted/50 px-3 py-2">
            <Loader2 className="h-3 w-3 animate-spin text-primary" />
            <span className="text-[11px] text-muted-foreground">Thinking and generating output...</span>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {chatError && (
        <p className="mb-2 rounded-lg border border-rose-500/20 bg-rose-500/10 px-2.5 py-1.5 text-[11px] text-rose-400">
          {chatError}
        </p>
      )}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              void handleSend()
            }
          }}
          placeholder="Ask Master Agent..."
          className="flex-1 rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
          disabled={sending}
        />
        <Button
          type="button"
          size="sm"
          variant={sending ? "destructive" : "default"}
          className="shrink-0"
          onClick={() => {
            if (sending) {
              handleStop()
              return
            }
            void handleSend()
          }}
          disabled={!canSend && !sending}
        >
          {sending ? <Square className="h-4 w-4" /> : <Send className="h-4 w-4" />}
          <span className="sr-only">{sending ? "Stop" : "Send"}</span>
        </Button>
      </div>
    </section>
  )
}
