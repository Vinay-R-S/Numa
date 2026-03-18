import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AgentChatMessage, sendAgentCommand } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
}

interface AiOutputProps {
  onCalendarRefresh?: () => void;
}

const initialMessages: Message[] = [
  {
    id: "1",
    role: "ai",
    content: "Hello! I'm Numa, your AI productivity assistant. Try asking me to schedule a meeting, set a reminder, or manage your calendar.",
  },
];

export default function AiOutput({ onCalendarRefresh }: AiOutputProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const query = input.trim();
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const history: AgentChatMessage[] = messages.slice(1).map((message) => ({
        role: message.role === "ai" ? "assistant" : "user",
        content: message.content,
      }));
      const data = await sendAgentCommand(query, history);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: data.response,
      };
      setMessages((prev) => [...prev, aiMsg]);

      if (data.refreshCalendar) {
        onCalendarRefresh?.();
      }
    } catch {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: "Sorry, I couldn't process that request. Please try again.",
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-primary animate-glow-pulse" />
        <h2 className="text-lg font-heading font-bold text-foreground">Output</h2>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 surface-panel p-4 overflow-auto space-y-4 mb-3 min-h-[130px] max-h-[240px] scroll-smooth"
      >
        {messages.map((msg, i) => (
          <div
            key={msg.id}
            className={cn(
              "flex items-start gap-2.5 animate-fade-in",
              msg.role === "user" && "justify-end"
            )}
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            {msg.role === "ai" && (
              <div className="mt-0.5 w-6 h-6 rounded-lg bg-primary/15 flex items-center justify-center shrink-0 ring-1 ring-primary/25 shadow-[0_0_10px_-3px_hsl(225_85%_63%/0.3)]">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
            )}
            <div
              className={cn(
                "text-sm leading-relaxed max-w-[80%] rounded-xl px-3.5 py-2.5 transition-all duration-200",
                msg.role === "ai"
                  ? "bg-accent/50 text-foreground/90 hover:bg-accent/60"
                  : "bg-primary/12 text-foreground border border-primary/15 hover:border-primary/25"
              )}
            >
              {msg.content}
            </div>
            {msg.role === "user" && (
              <div className="mt-0.5 w-6 h-6 rounded-lg bg-muted flex items-center justify-center shrink-0 ring-1 ring-secondary/20">
                <User className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}

        {isTyping && (
          <div className="flex items-start gap-2.5">
            <div className="mt-0.5 w-6 h-6 rounded-lg bg-primary/15 flex items-center justify-center shrink-0 ring-1 ring-primary/25 shadow-[0_0_10px_-3px_hsl(225_85%_63%/0.3)]">
              <Bot className="w-3.5 h-3.5 text-primary" />
            </div>
            <div className="bg-accent/50 rounded-xl px-4 py-3 flex gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Schedule a meeting tomorrow at 4pm"
          className="flex-1 surface-panel px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 focus:border-primary/30 transition-all duration-300"
        />
        <Button
          variant="glow"
          size="icon"
          onClick={handleSend}
          disabled={isTyping || !input.trim()}
          className="transition-all duration-300"
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
