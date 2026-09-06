import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * The message of an Error, or `fallback` for anything else.
 *
 * One definition: `features/settings` and `features/productivity` each carried a
 * verbatim copy (NUMA-142 P6, PLAN 10).
 */
export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}
