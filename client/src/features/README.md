# Feature modules

One self-contained module per domain feature (NUMA-110 P4, PLAN 5.3 / 21.2).
Populated incrementally by the Tier 1 frontend slices; pages become thin
route + layout + composition and consume a feature's hook.

## Module shape

```
features/<feature>/
  <feature>.api.ts        # typed fetchers built on lib/http (no React)
  <feature>.types.ts      # domain types/interfaces
  <feature>.schema.ts     # zod schemas (validation + preprocessing)
  <feature>.transforms.ts # pure API-DTO -> view-model mappers
  use<Feature>.ts         # data hook: fetch + validate + transform + cache + state
  components/             # presentational pieces (props in, events out)
  index.ts               # public surface of the module
```

## Rules

- `<feature>.api.ts` uses the shared `http` client from `lib/http.ts`. No
  re-declared `authHeaders`/`parseJson`, no raw `fetch`.
- Validate inputs and API responses with zod (`lib/validation` primitives +
  the feature's `<feature>.schema.ts`); surface errors as the typed `ApiError`.
- Hooks own loading/error/data state; components only render and dispatch.
- A page imports a hook and composes components. No `fetch`, no data massaging,
  no SQL-shaped logic in a page.

## Migration notes (preserve behavior)

When moving an existing `*Api.ts` onto `http`, keep these per-endpoint concerns
in the feature's `api.ts` (they are intentionally not in the shared client):

- Curated error text: pass the old fallback string via the `errorMessage`
  option so a body-less error still reads the same.
- 200-with-`{ success: false }` envelopes (agent chat endpoints): keep the
  explicit `if (!res.success) throw` check in the feature method.
- Sentinel-string errors (e.g. `CALENDAR_NOT_CONNECTED`): switch callers to
  inspect the typed `ApiError` (`err.status === 401` / `err.detail`) instead.
- Response caching: pass `cache: "no-store"` where the old code did.
- Base URL: `http` honors `NEXT_PUBLIC_API_URL`; files that hardcoded it lose
  nothing.

## Migration source map (PLAN 17.5)

Complete as of NUMA-118: every `*Api.ts` now lives in its feature module on
`lib/http`, and `src/components/` holds only shared UI (`ui/`, `sections/`,
`tasklist/` layout chrome) plus the top-level page components.

| Was | Now | Landed on |
|---|---|---|
| `components/tasklist/api.ts` | `features/tasks/tasks.api.ts` | NUMA-111 |
| `components/journal/journalApi.ts` | `features/journal/journal.api.ts` | NUMA-112 |
| `components/calendar/api.ts` | `features/calendar/calendar.api.ts` | NUMA-114 |
| `components/agents/slackAgentApi.ts` | `features/slack/slack.api.ts` | NUMA-115 |
| `components/health/healthApi.ts` | `features/health/health.api.ts` | NUMA-116 |
| `components/productivity/productivityApi.ts` | `features/productivity/productivity.api.ts` | NUMA-117 |
| `components/agents/masterAgentApi.ts` | `features/agents/masterAgent.api.ts` | NUMA-118 |

## Shared agent surface (NUMA-118)

`features/agents/` owns the master agent and everything the four docks share:

- `useAgentChat` - the chat loop (open/close with Escape, composer, in-flight
  guard, send with abort, "Generation stopped." on abort, error bubble,
  suggestion prefill). Feature hooks supply a transcript adapter, the sender and
  the post-reply refresh; they keep their own public return shape.
- `AgentDockPanel` - the complete sub-agent dock that slack and health both
  render. Calendar and the master agent keep their own layouts and share only
  `AgentDockShell` + `AgentMessageContent`.
