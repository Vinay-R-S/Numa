/**
 * Tasks validation schemas (NUMA-111 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the backend Pydantic bounds in `server/src/tasks/schemas.py`. Response
 * schemas run in `tasks.api.ts` via the shared `http` `schema` option so runtime
 * data is type-safe and API contract drift fails loudly. Timestamp/id fields are
 * kept as plain strings so naive/aware datetime serialization is tolerated while
 * response structure is still validated. Input schemas mirror TaskCreate/Update
 * for the form layer.
 */
import { z } from "@/lib/validation"

export const taskStatusSchema = z.enum(["planned", "inprogress", "completed", "pending"])
export const taskPrioritySchema = z.enum(["low", "medium", "high", "urgent"])

export const taskSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  title: z.string(),
  description: z.string().nullish(),
  status: taskStatusSchema,
  priority: taskPrioritySchema.nullish(),
  due_date: z.string().nullish(),
  reminder_at: z.string().nullish(),
  source_name: z.string().nullish(),
  source_logo: z.string().nullish(),
  external_ref: z.string().nullish(),
  position: z.number(),
  completed_at: z.string().nullish(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const taskListSchema = z.array(taskSchema)

const statBucketSchema = z.array(z.object({ status: z.string(), count: z.number() }))
const dateBucketSchema = z.array(z.object({ date: z.string(), count: z.number() }))

export const taskStatsSchema = z.object({
  total: z.number(),
  streak: z.number(),
  by_status: statBucketSchema,
  daily: dateBucketSchema,
  weekly: dateBucketSchema,
  monthly: dateBucketSchema,
  yearly: dateBucketSchema,
})

// Input: mirrors backend TaskCreate / TaskUpdate for the form layer.
export const taskCreateSchema = z.object({
  title: z.string().trim().min(1),
  description: z.string().trim().optional(),
  status: taskStatusSchema.default("planned"),
  priority: taskPrioritySchema.optional(),
  due_date: z.string().optional(),
  reminder_at: z.string().optional(),
  source_name: z.string().optional(),
  source_logo: z.string().optional(),
  position: z.number().int().default(0),
})

export const taskUpdateSchema = taskCreateSchema.partial()

export type TaskCreateInput = z.infer<typeof taskCreateSchema>
export type TaskUpdateInput = z.infer<typeof taskUpdateSchema>
