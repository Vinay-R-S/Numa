const DOTS = [0, 1, 2, 3, 4]

export function DifficultyDots({ level }: { level: number }) {
  return (
    <div className="flex gap-1">
      {DOTS.map((index) => (
        <span
          key={index}
          className={`h-1.5 w-1.5 rounded-full ${index < level ? "bg-primary" : "bg-border/40"}`}
        />
      ))}
    </div>
  )
}
