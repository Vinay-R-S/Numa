"use client"

import React from "react"
import { Leaf, Headphones } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EntryScreenProps {
  onBegin: () => void
}

export function EntryScreen({ onBegin }: EntryScreenProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="text-center max-w-md">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-border/40 bg-card/40">
          <Leaf className="h-8 w-8 text-primary" />
        </div>

        <h1 className="text-3xl font-bold text-foreground sm:text-4xl">
          Mental Peace
        </h1>

        <p className="mt-3 text-sm text-muted-foreground sm:text-base">
          Your space for stillness, breath, and healing
        </p>

        <Button
          onClick={onBegin}
          size="lg"
          className="mt-8 px-8"
        >
          Begin Your Practice
        </Button>

        <p className="mt-6 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Headphones className="h-3.5 w-3.5" />
          Best experienced with headphones
        </p>
      </div>
    </div>
  )
}
