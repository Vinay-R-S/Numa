import { LEETCODE_DIFFICULTY_ROWS } from "../productivity.constants"
import type { LeetCodeStats } from "../productivity.types"
import { leetCodeTotalProblems } from "../productivity.utils"
import { DifficultyBar } from "./DifficultyBar"

export function DifficultyBreakdown({ stats }: { stats: LeetCodeStats }) {
  const total = leetCodeTotalProblems(stats)

  return (
    <div className="space-y-3 rounded-xl border border-border/40 bg-background/30 p-4">
      {LEETCODE_DIFFICULTY_ROWS.map((row) => (
        <DifficultyBar
          key={row.key}
          label={row.label}
          solved={row.solved(stats)}
          total={total}
          color={row.color}
          bgColor={row.bgColor}
        />
      ))}
    </div>
  )
}
