"use client"

import { useState } from "react"
import { Heart, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { REFLECTION_PROMPTS } from "../mentalPeace.constants"

interface ReflectionCardProps {
  onComplete: () => void
}

/**
 * Post-practice reflection prompts. Not mounted by any stage today; kept as the
 * feature's own component (NUMA-120 moved it, it is not new) so wiring it into
 * the flow stays a one-line change.
 */
export function ReflectionCard({ onComplete }: ReflectionCardProps) {
  const [currentPrompt, setCurrentPrompt] = useState(0)
  const [reflection, setReflection] = useState("")

  const handleNext = () => {
    if (currentPrompt >= REFLECTION_PROMPTS.length - 1) {
      onComplete()
      return
    }

    setCurrentPrompt(currentPrompt + 1)
    setReflection("")
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-3 sm:px-6">
      <div className="w-full max-w-lg">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-border/40 bg-card/40">
            <Sparkles className="h-7 w-7 text-primary" />
          </div>
          <h2 className="text-xl font-bold text-foreground sm:text-2xl">
            Beautiful Practice
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Take a moment to reflect on your experience
          </p>
        </div>

        <div className="mb-6 rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-6">
          <div className="mb-6 flex justify-center gap-2">
            {REFLECTION_PROMPTS.map((prompt, i) => (
              <div
                key={prompt}
                className={`h-2 w-2 rounded-full transition-colors ${
                  i === currentPrompt ? "bg-primary" : i < currentPrompt ? "bg-primary/50" : "bg-border/40"
                }`}
              />
            ))}
          </div>

          <h3 className="mb-6 text-center text-lg font-medium text-foreground">
            {REFLECTION_PROMPTS[currentPrompt]}
          </h3>

          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="Write your thoughts here... (optional)"
            className="h-28 w-full resize-none rounded-xl border border-border/40 bg-background p-3 text-foreground placeholder:text-muted-foreground/60 focus:border-primary/50 focus:outline-none sm:h-32 sm:p-4"
          />
        </div>

        <div className="flex gap-3 sm:gap-4">
          <Button variant="outline" onClick={onComplete} className="flex-1">
            Skip Reflection
          </Button>
          <Button onClick={handleNext} className="flex-1 gap-2">
            {currentPrompt < REFLECTION_PROMPTS.length - 1 ? (
              "Next"
            ) : (
              <>
                <Heart className="h-4 w-4" /> Complete
              </>
            )}
          </Button>
        </div>

        <p className="mt-8 text-center text-sm text-muted-foreground">
          The light in me honors the light in you
        </p>
      </div>
    </div>
  )
}
