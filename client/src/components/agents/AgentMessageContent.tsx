import React from "react"

const EMOJI_PATTERN = /[\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\uFE0F\u200D]/gu

function cleanAgentText(text: string): string {
  return text
    .replace(EMOJI_PATTERN, "")
    .replace(/<mailto:([^|>]+)\|([^>]+)>/g, "$2")
    .replace(/<([^|>]+)\|([^>]+)>/g, "$2")
    .replace(/<([^>]+)>/g, "$1")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim()
}

function renderInlineMarkdown(text: string, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g)

  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`

    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={key} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      )
    }

    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code key={key} className="rounded bg-background/70 px-1 py-0.5 text-[0.92em]">
          {part.slice(1, -1)}
        </code>
      )
    }

    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return (
        <em key={key} className="italic">
          {part.slice(1, -1)}
        </em>
      )
    }

    return <React.Fragment key={key}>{part}</React.Fragment>
  })
}

function isTableDivider(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed.includes("|")) return false
  return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(trimmed)
}

function isTableLine(line: string): boolean {
  const trimmed = line.trim()
  return trimmed.includes("|") && trimmed.split("|").filter((cell) => cell.trim()).length >= 2
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim())
}

function TableBlock({ lines, blockIndex }: { lines: string[]; blockIndex: number }) {
  const rows = lines.filter((line) => !isTableDivider(line)).map(splitTableRow)
  if (rows.length === 0) return null

  const [head, ...body] = rows

  return (
    <div className="my-2 max-w-full overflow-hidden rounded-lg border border-border/40 bg-background/30">
      <table className="w-full table-fixed border-collapse text-left text-xs">
        <thead className="bg-muted/40 text-foreground">
          <tr>
            {head.map((cell, cellIndex) => (
              <th key={`table-${blockIndex}-head-${cellIndex}`} className="border-b border-border/40 px-2 py-1.5 align-top font-semibold break-words [overflow-wrap:anywhere]">
                {renderInlineMarkdown(cell, `table-${blockIndex}-head-${cellIndex}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, rowIndex) => (
            <tr key={`table-${blockIndex}-row-${rowIndex}`} className="border-t border-border/20">
              {head.map((_, cellIndex) => (
                <td key={`table-${blockIndex}-cell-${rowIndex}-${cellIndex}`} className="px-2 py-1.5 align-top text-muted-foreground break-words [overflow-wrap:anywhere]">
                  {renderInlineMarkdown(row[cellIndex] ?? "", `table-${blockIndex}-cell-${rowIndex}-${cellIndex}`)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ParagraphLine({ line, index }: { line: string; index: number }) {
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
      <div key={`ul-${index}`} className="flex min-w-0 gap-2">
        <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/70" />
        <span className="min-w-0 flex-1 break-words [overflow-wrap:anywhere]">
          {renderInlineMarkdown(unordered[1], `ul-${index}`)}
        </span>
      </div>
    )
  }

  const ordered = trimmed.match(/^(\d+)[.)]\s+(.+)$/)
  if (ordered) {
    return (
      <div key={`ol-${index}`} className="flex min-w-0 gap-2">
        <span className="shrink-0 tabular-nums text-muted-foreground">{ordered[1]}.</span>
        <span className="min-w-0 flex-1 break-words [overflow-wrap:anywhere]">
          {renderInlineMarkdown(ordered[2], `ol-${index}`)}
        </span>
      </div>
    )
  }

  return (
    <p key={`p-${index}`} className="break-words [overflow-wrap:anywhere]">
      {renderInlineMarkdown(line, `p-${index}`)}
    </p>
  )
}

export function AgentMessageContent({ content }: { content: string }) {
  const cleaned = cleanAgentText(content)
  const lines = cleaned.split(/\r?\n/)

  if (!cleaned) {
    return null
  }

  const blocks: React.ReactNode[] = []
  let index = 0

  while (index < lines.length) {
    if (isTableLine(lines[index]) && lines[index + 1] && isTableDivider(lines[index + 1])) {
      const tableLines = [lines[index], lines[index + 1]]
      index += 2

      while (index < lines.length && isTableLine(lines[index])) {
        tableLines.push(lines[index])
        index += 1
      }

      blocks.push(<TableBlock key={`table-${index}`} lines={tableLines} blockIndex={index} />)
      continue
    }

    blocks.push(<ParagraphLine key={`line-${index}`} line={lines[index]} index={index} />)
    index += 1
  }

  return (
    <div className="min-w-0 max-w-full space-y-1.5 overflow-hidden whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
      {blocks}
    </div>
  )
}
