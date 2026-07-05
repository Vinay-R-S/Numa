/**
 * Shared client validation home (NUMA-110 P4, PLAN 22.2 / 22.3).
 *
 * Central place for reusable zod primitives that mirror backend Pydantic bounds.
 * Per-feature schemas live in each module's `<feature>.schema.ts` and compose
 * these; response validation runs in `lib/http.ts` via the request `schema`
 * option. The backend stays authoritative; these catch bad input client-side
 * first and fail loudly on API contract drift.
 */
import { z } from "zod"

export const nonEmptyString = z.string().trim().min(1)
export const optionalString = z.string().trim().optional()
export const email = z.string().trim().toLowerCase().pipe(z.email())
export const isoDateTime = z.iso.datetime({ offset: true, local: true })

export { z }
