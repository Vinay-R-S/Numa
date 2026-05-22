import React from "react"

const EMOJI_PATTERN = /[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\uFE0F\u200D]/gu

function cleanAgentText(text: string): string {
  return text
    .replace(EMOJI_PATTERN, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim()
}

function renderInlineMarkdown(text: string, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={key} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>
    }
    return <React.Fragment key={key}>{part}</React.Fragment>
  })
}

export function AgentMessageContent({ content }: { content: string }) {
  const cleaned = cleanAgentText(content)
  const lines = cleaned.split(/\r?\n/)

  if (!cleaned) {
    return null
  }

  return (
    <div className="space-y-1.5 whitespace-pre-wrap break-words">
      {lines.map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) {
          return <div key={`blank-${index}`} className="h-1" />
        }

        const heading = trimmed.match(/^#{1,6}\s+(.+)$/)
        if (heading) {
          return (
            <p key={`heading-${index}`} className="font-semibold text-foreground">
              {renderInlineMarkdown(heading[1], `heading-${index}`)}
            </p>
          )
        }

        const unordered = trimmed.match(/^[-*]\s+(.+)$/)
        if (unordered) {
          return (
            <div key={`ul-${index}`} className="flex gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/70" />
              <span>{renderInlineMarkdown(unordered[1], `ul-${index}`)}</span>
            </div>
          )
        }

        const ordered = trimmed.match(/^(\d+)[.)]\s+(.+)$/)
        if (ordered) {
          return (
            <div key={`ol-${index}`} className="flex gap-2">
              <span className="shrink-0 tabular-nums text-muted-foreground">{ordered[1]}.</span>
              <span>{renderInlineMarkdown(ordered[2], `ol-${index}`)}</span>
            </div>
          )
        }

        return (
          <p key={`p-${index}`}>
            {renderInlineMarkdown(line, `p-${index}`)}
          </p>
        )
      })}
    </div>
  )
}
