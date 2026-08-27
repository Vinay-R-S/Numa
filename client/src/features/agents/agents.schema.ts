/**
 * Master agent response schemas (NUMA-118 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors `server/src/master_agent/schemas.py`. The `z.ZodType<...>`
 * annotations tie each schema to its type in `agents.types.ts`, so the two
 * cannot drift apart silently.
 *
 * The refresh flags are `optional` rather than required: the server defaults
 * them to `false` and always emits them under its `response_model`, but the
 * hook reads them as booleans either way and a missing flag must not blank the
 * agent's answer.
 *
 * `fetch-latest` is validated loosely on purpose. `results` and `retention` are
 * bare `list[dict]` / `dict` on the server, no caller reads either one (both
 * call sites discard the response), and the old code ran no validation at all,
 * so a strict shape here would only invent a new way for a payload nobody reads
 * to fail.
 */
import { z } from "@/lib/validation"
import type { MasterAgentFetchLatestResponse, MasterAgentResponse } from "./agents.types"

export const masterAgentResponseSchema: z.ZodType<MasterAgentResponse> = z.object({
  response: z.string(),
  success: z.boolean(),
  delegated_to: z.string().nullish(),
  refreshCalendar: z.boolean().optional(),
  refreshTasks: z.boolean().optional(),
  refreshSlack: z.boolean().optional(),
  refreshHealth: z.boolean().optional(),
  refreshGithub: z.boolean().optional(),
  refreshJournal: z.boolean().optional(),
})

export const masterAgentFetchLatestSchema: z.ZodType<MasterAgentFetchLatestResponse> = z.object({
  ok: z.boolean(),
  scope: z.string(),
  users: z.number(),
  results: z.array(z.looseObject({})),
  retention: z.looseObject({}),
})
