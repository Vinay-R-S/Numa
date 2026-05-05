"use client"

import React, { useState } from "react"
import { Heart, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ReflectionCardProps {
  onComplete: () => void
}

const reflectionPrompts = [
  "How does your body feel right now?",
  "What thoughts came up during your practice?",
  "What are you grateful for in this moment?",
  "Is there anything you want to let go of?",
]

export function ReflectionCard({ onComplete }: ReflectionCardProps) {
  const [currentPrompt, setCurrentPrompt] = useState(0)
  const [reflection, setReflection] = useState("")

  const handleNext = () => {
    if (currentPrompt < reflectionPrompts.length - 1) {
      setCurrentPrompt(currentPrompt + 1)
      setReflection("")
    } else {
      onComplete()
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-3 sm:px-6">
      <div className="w-full max-w-lg">
        {/* Header */}
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

        {/* Reflection card */}
        <div className="mb-6 rounded-2xl border border-border/40 bg-card/40 p-4 sm:p-6">
          {/* Progress dots */}
          <div className="mb-6 flex justify-center gap-2">
            {reflectionPrompts.map((_, i) => (
              <div
                key={i}
                className={`h-2 w-2 rounded-full transition-colors ${
                  i === currentPrompt
                    ? "bg-primary"
                    : i < currentPrompt
                      ? "bg-primary/50"
                      : "bg-border/40"
                }`}
              />
            ))}
          </div>

          {/* Prompt */}
          <h3 className="mb-6 text-center text-lg font-medium text-foreground">
            {reflectionPrompts[currentPrompt]}
          </h3>

          {/* Text area */}
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="Write your thoughts here... (optional)"
            className="h-28 w-full resize-none rounded-xl border border-border/40 bg-background p-3 text-foreground placeholder:text-muted-foreground/60 focus:border-primary/50 focus:outline-none sm:h-32 sm:p-4"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 sm:gap-4">
          <Button
            variant="outline"
            onClick={onComplete}
            className="flex-1"
          >
            Skip Reflection
          </Button>
          <Button
            onClick={handleNext}
            className="flex-1 gap-2"
          >
            {currentPrompt < reflectionPrompts.length - 1 ? (
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
