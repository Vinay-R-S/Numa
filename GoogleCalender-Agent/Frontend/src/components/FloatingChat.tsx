import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AgentChatMessage, sendAgentCommand } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
}

const initialMessages: Message[] = [
  {
    id: "1",
    role: "ai",
    content:
      "Hey! I'm Numa. Tell me what to add, move, or remove from your calendar — just talk naturally.",
  },
];

interface FloatingChatProps {
  onCalendarRefresh?: () => void;
}

export default function FloatingChat({ onCalendarRefresh }: FloatingChatProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping, open]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Listen for quick action fill events
  useEffect(() => {
    const handler = (e: CustomEvent<string>) => {
      setOpen(true);
      setInput(e.detail);
      setTimeout(() => inputRef.current?.focus(), 100);
    };
    window.addEventListener("numa-fill-chat", handler as EventListener);
    return () => window.removeEventListener("numa-fill-chat", handler as EventListener);
  }, []);

  // Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => {
          if (!v) setTimeout(() => inputRef.current?.focus(), 100);
          return !v;
        });
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const query = input.trim();
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const history: AgentChatMessage[] = messages.slice(1).map((message) => ({
        role: message.role === "ai" ? "assistant" : "user",
        content: message.content,
      }));
      const data = await sendAgentCommand(query, history);
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "ai", content: data.response },
      ]);
      if (data.refreshCalendar) onCalendarRefresh?.();
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "ai",
          content: "Sorry, I couldn't process that. Please try again.",
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      {/* Inline trigger button — same style as quick action buttons */}
      <button
        onClick={() => {
          setOpen((v) => !v);
          if (!open) setTimeout(() => inputRef.current?.focus(), 150);
        }}
        className={cn(
          "flex items-center gap-2 px-5 py-3 text-sm font-semibold rounded-xl border transition-all duration-300",
          open
            ? "border-primary/40 bg-primary/15 text-foreground shadow-[0_0_16px_-4px_hsl(var(--primary)/0.3)]"
            : "border-border/20 bg-accent/30 text-muted-foreground hover:text-foreground hover:bg-accent/50 hover:border-primary/30 hover:shadow-[0_0_16px_-4px_hsl(var(--primary)/0.25)]"
        )}
      >
        <Bot className="w-5 h-5" />
        Numa AI
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
      </button>

      {/* Popup chat panel */}
      {open && (
        <div className="absolute top-full right-0 mt-2 w-[400px] z-[120] animate-scale-in">
          <div className="glass-panel rounded-2xl shadow-[0_8px_48px_-12px_hsl(var(--primary)/0.25),0_0_0_1px_hsl(var(--border)/0.1)] overflow-hidden" style={{ background: "hsla(250, 20%, 12%, 0.55)", backdropFilter: "blur(28px) saturate(1.4)" }}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/20">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-primary/15 flex items-center justify-center ring-1 ring-primary/25 shadow-[0_0_10px_-3px_hsl(var(--primary)/0.3)]">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                </div>
                <span className="text-sm font-heading font-semibold text-foreground">Numa AI</span>
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div
              ref={scrollRef}
              className="p-4 overflow-auto space-y-4 scroll-smooth"
              style={{ maxHeight: 320, minHeight: 160 }}
            >
              {messages.map((msg, i) => (
                <div
                  key={msg.id}
                  className={cn(
                    "flex items-end gap-2 animate-fade-in",
                    msg.role === "user" ? "justify-end" : "justify-start"
                  )}
                  style={{ animationDelay: `${i * 0.04}s` }}
                >
                  {msg.role === "ai" && (
                    <div className="w-5 h-5 rounded-full bg-primary/15 flex items-center justify-center shrink-0 ring-1 ring-primary/25 mb-0.5">
                      <Bot className="w-2.5 h-2.5 text-primary" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "text-[13px] leading-relaxed max-w-[80%] px-3.5 py-2.5 transition-all duration-300",
                      msg.role === "ai"
                        ? "bg-accent/40 text-foreground/90 rounded-2xl rounded-bl-md border border-border/10"
                        : "bg-gradient-to-br from-primary/20 to-secondary/10 text-foreground rounded-2xl rounded-br-md border border-primary/20 shadow-[0_0_12px_-4px_hsl(var(--primary)/0.2)]"
                    )}
                  >
                    {msg.content}
                  </div>
                  {msg.role === "user" && (
                    <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center shrink-0 ring-1 ring-border/30 mb-0.5">
                      <User className="w-2.5 h-2.5 text-muted-foreground" />
                    </div>
                  )}
                </div>
              ))}

              {isTyping && (
                <div className="flex items-end gap-2">
                  <div className="w-5 h-5 rounded-full bg-primary/15 flex items-center justify-center shrink-0 ring-1 ring-primary/25 mb-0.5">
                    <Bot className="w-2.5 h-2.5 text-primary" />
                  </div>
                  <div className="bg-accent/40 rounded-2xl rounded-bl-md px-4 py-3 flex gap-1.5 border border-border/10">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="flex items-center gap-2 p-3 border-t border-border/20">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="Ask Numa anything… (Ctrl+K)"
                className="flex-1 bg-muted/40 rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all duration-200"
              />
              <Button
                variant="glow"
                size="icon"
                className="w-8 h-8 shrink-0"
                onClick={handleSend}
                disabled={isTyping || !input.trim()}
              >
                <Send className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
