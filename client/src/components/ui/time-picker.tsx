"use client"

import * as React from "react"
import { Clock } from "lucide-react"
import { cn } from "@/lib/utils"

interface TimePickerProps {
  value?: string        // "HH:MM" (24-hour)
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function TimePicker({ value, onChange, className, disabled }: TimePickerProps) {
  // Derive 12-hour parts from the 24-hour value prop
  const { displayHour, displayMinute, isAm } = React.useMemo(() => {
    if (!value) return { displayHour: "", displayMinute: "", isAm: true }
    const [hStr, mStr] = value.split(":")
    const h = parseInt(hStr, 10)
    const m = parseInt(mStr, 10)
    if (isNaN(h) || isNaN(m)) return { displayHour: "", displayMinute: "", isAm: true }
    const am = h < 12
    const h12 = h % 12 === 0 ? 12 : h % 12
    return {
      displayHour: String(h12),
      displayMinute: String(m).padStart(2, "0"),
      isAm: am,
    }
  }, [value])

  function emit(h12: number, min: number, am: boolean) {
    let h24: number
    if (am) {
      h24 = h12 === 12 ? 0 : h12
    } else {
      h24 = h12 === 12 ? 12 : h12 + 12
    }
    const hh = String(h24).padStart(2, "0")
    const mm = String(min).padStart(2, "0")
    onChange(`${hh}:${mm}`)
  }

  function handleHourChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value
    if (raw === "") { onChange(""); return }
    let h = parseInt(raw, 10)
    if (isNaN(h)) return
    if (h < 1) h = 1
    if (h > 12) h = 12
    const min = displayMinute ? parseInt(displayMinute, 10) : 0
    emit(h, isNaN(min) ? 0 : min, isAm)
  }

  function handleMinuteChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value
    if (raw === "") { onChange(""); return }
    let m = parseInt(raw, 10)
    if (isNaN(m)) return
    if (m < 0) m = 0
    if (m > 59) m = 59
    const h = displayHour ? parseInt(displayHour, 10) : 12
    emit(isNaN(h) ? 12 : h, m, isAm)
  }

  function handleAmPm(am: boolean) {
    const h = displayHour ? parseInt(displayHour, 10) : 12
    const m = displayMinute ? parseInt(displayMinute, 10) : 0
    emit(isNaN(h) ? 12 : h, isNaN(m) ? 0 : m, am)
  }

  const hasValue = displayHour !== ""

  return (
    <div
      className={cn(
        "inline-flex items-center h-9 rounded-md border border-input bg-background px-2 text-sm gap-0.5",
        disabled && "opacity-50 pointer-events-none",
        className
      )}
    >
      <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      {/* Hour */}
      <input
        type="number"
        min={1}
        max={12}
        placeholder="12"
        value={displayHour}
        onChange={handleHourChange}
        className="w-7 bg-transparent text-center focus:outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      />
      <span className="text-muted-foreground select-none leading-none">:</span>
      {/* Minute */}
      <input
        type="number"
        min={0}
        max={59}
        placeholder="00"
        value={displayMinute}
        onChange={handleMinuteChange}
        className="w-7 bg-transparent text-center focus:outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      />
      {/* AM/PM */}
      <div className="flex rounded overflow-hidden bg-muted/50 text-xs shrink-0 ml-0.5">
        <button
          type="button"
          onClick={() => handleAmPm(true)}
          className={cn(
            "px-1.5 py-1 transition-colors font-medium",
            hasValue && isAm
              ? "bg-primary text-primary-foreground rounded-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          AM
        </button>
        <button
          type="button"
          onClick={() => handleAmPm(false)}
          className={cn(
            "px-1.5 py-1 transition-colors font-medium",
            hasValue && !isAm
              ? "bg-primary text-primary-foreground rounded-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          PM
        </button>
      </div>
    </div>
  )
}
