import { GITHUB_STAT_CHIPS } from "../productivity.constants"
import type { GitHubStats } from "../productivity.types"
import { StatChip } from "./StatChip"

export function GitHubStatsGrid({ stats }: { stats: GitHubStats | null }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
      {GITHUB_STAT_CHIPS.map((chip) => (
        <StatChip
          key={chip.key}
          icon={chip.icon}
          label={chip.label}
          value={chip.value(stats)}
          color={chip.color}
        />
      ))}
    </div>
  )
}
