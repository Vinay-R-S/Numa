"use client"

import * as React from "react"
import { Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"

interface TimePickerProps {
  value?: string        // "HH:MM" (24-hour)
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function TimePicker({ value, onChange, placeholder = "Pick a time", className, disabled }: TimePickerProps) {
  const [open, setOpen] = React.useState(false)

  const [selectedHour, selectedMinute] = React.useMemo(() => {
    if (!value) return [null, null]
    const parts = value.split(":")
    const h = parseInt(parts[0], 10)
    const m = parseInt(parts[1], 10)
    if (isNaN(h) || isNaN(m)) return [null, null]
    return [h, m]
  }, [value])

  const hours = Array.from({ length: 24 }, (_, i) => i)
  const minutes = Array.from({ length: 12 }, (_, i) => i * 5)

  function handleSelect(h: number, m: number) {
    const hh = String(h).padStart(2, "0")
    const mm = String(m).padStart(2, "0")
    onChange(`${hh}:${mm}`)
    setOpen(false)
  }

  const displayValue = React.useMemo(() => {
    if (selectedHour === null || selectedMinute === null) return null
    const h = selectedHour % 12 === 0 ? 12 : selectedHour % 12
    const ampm = selectedHour < 12 ? "AM" : "PM"
    const mm = String(selectedMinute).padStart(2, "0")
    return `${h}:${mm} ${ampm}`
  }, [selectedHour, selectedMinute])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            "w-full justify-start text-left font-normal",
            !displayValue && "text-muted-foreground",
            className
          )}
        >
          <Clock className="mr-2 h-4 w-4 shrink-0" />
          {displayValue ?? <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0" align="start">
        <div className="flex divide-x divide-border">
          {/* Hours */}
          <ScrollArea className="h-52 flex-1">
            <div className="p-1 space-y-0.5">
              {hours.map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => handleSelect(h, selectedMinute ?? 0)}
                  className={cn(
                    "w-full text-sm text-left px-2.5 py-1 rounded hover:bg-accent hover:text-accent-foreground transition-colors",
                    selectedHour === h && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
                  )}
                >
                  {String(h % 12 === 0 ? 12 : h % 12).padStart(2, "0")}{" "}
                  <span className="text-xs opacity-60">{h < 12 ? "AM" : "PM"}</span>
                </button>
              ))}
            </div>
          </ScrollArea>
          {/* Minutes */}
          <ScrollArea className="h-52 flex-1">
            <div className="p-1 space-y-0.5">
              {minutes.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => handleSelect(selectedHour ?? 9, m)}
                  className={cn(
                    "w-full text-sm text-left px-2.5 py-1 rounded hover:bg-accent hover:text-accent-foreground transition-colors",
                    selectedMinute === m && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
                  )}
                >
                  {String(m).padStart(2, "0")} min
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>
      </PopoverContent>
    </Popover>
  )
}
