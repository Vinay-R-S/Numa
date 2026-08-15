import type { LeetCodeStats } from "../productivity.types"

const CARD_CLASS =
  "flex flex-row items-center gap-3 rounded-xl border border-border/40 bg-background/40 p-3 sm:flex-col sm:gap-1"
const VALUE_CLASS = "text-xl font-black tabular-nums sm:text-2xl"
const LABEL_CLASS = "text-xs text-muted-foreground font-medium sm:text-[10px]"

export function LeetCodeSummary({ stats }: { stats: LeetCodeStats }) {
  const cards = [
    { key: "solved", label: "Solved", value: String(stats.total_solved), color: "text-foreground" },
    {
      key: "acceptance",
      label: "Acceptance",
      value: `${stats.acceptance_rate.toFixed(1)}%`,
      color: "text-foreground",
    },
    {
      key: "ranking",
      label: "Ranking",
      value: `#${stats.ranking.toLocaleString()}`,
      color: "text-amber-400",
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:gap-2.5">
      {cards.map((card) => (
        <div key={card.key} className={CARD_CLASS}>
          <span className={`${VALUE_CLASS} ${card.color}`}>{card.value}</span>
          <span className={LABEL_CLASS}>{card.label}</span>
        </div>
      ))}
    </div>
  )
}
