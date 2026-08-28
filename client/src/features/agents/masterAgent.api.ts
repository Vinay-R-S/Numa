/**
 * Master agent API (NUMA-118 P4, PLAN 17.5 / 21.2).
 *
 * Moved from `components/agents/masterAgentApi.ts` onto the shared `http`
 * client. Behavior preserved from that file:
 *
 * - `sendMasterAgentCommand` still short-circuits when the local AI toggle is
 *   off, and still throws on the 200-with-`{ success: false }` agent envelope.
 * - Per-endpoint fallback error text ("Master agent request failed", "Failed to
 *   fetch latest app data") is passed through `errorMessage`, so a body-less
 *   error still reads the same.
 * - `fetch-latest` still sends `background=true` only when asked; the server
 *   reads it as a query parameter and takes no request body.
 * - Both endpoints answer with JSON, so `expectBody` turns a body-less or
 *   non-JSON 2xx into the endpoint's error instead of resolving `undefined`.
 */
import { expectBody, http } from "@/lib/http"
// Deep import of the leaf storage module: the settings barrel would pull the
// whole settings UI into this bundle for one localStorage read.
import { getLocalAiEnabled } from "@/features/settings/settings.storage"
import { masterAgentFetchLatestSchema, masterAgentResponseSchema } from "./agents.schema"
import type {
  FetchLatestOptions,
  MasterAgentFetchLatestResponse,
  MasterAgentMessage,
  MasterAgentResponse,
} from "./agents.types"

const CHAT_ERROR = "Master agent request failed"
const FETCH_LATEST_ERROR = "Failed to fetch latest app data"

export async function sendMasterAgentCommand(
  query: string,
  history: MasterAgentMessage[] = [],
  signal?: AbortSignal
): Promise<MasterAgentResponse> {
  if (!getLocalAiEnabled()) {
    throw new Error("AI agents are disabled in Settings.")
  }

  const data = await expectBody(
    http.post("/master-agent/chat", { query, history }, {
      signal,
      schema: masterAgentResponseSchema,
      errorMessage: CHAT_ERROR,
    }),
    CHAT_ERROR
  )

  if (data.success === false) {
    throw new Error(data.response || CHAT_ERROR)
  }

  return data
}

export function fetchLatestAgentData(
  options: FetchLatestOptions = {}
): Promise<MasterAgentFetchLatestResponse> {
  return expectBody(
    http.post("/master-agent/fetch-latest", undefined, {
      query: options.background ? { background: true } : undefined,
      schema: masterAgentFetchLatestSchema,
      errorMessage: FETCH_LATEST_ERROR,
    }),
    FETCH_LATEST_ERROR
  )
}
