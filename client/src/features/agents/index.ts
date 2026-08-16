/**
 * Agents feature module public surface (NUMA-118 P4, PLAN 5.3 / 21.2).
 *
 * Holds the master agent (its API, hook and dock) plus the pieces every feature
 * dock shares: the chat loop `useAgentChat`, the dock frame, the transcript
 * renderer and the sub-agent panel that slack and health both render.
 */
export * from "./agents.types"
export * from "./agents.constants"
export * from "./agents.schema"
export * from "./masterAgent.api"

export { useAgentChat } from "./useAgentChat"
export type {
  AgentChatResult,
  AgentTranscript,
  UseAgentChatOptions,
  UseAgentChatReturn,
} from "./useAgentChat"
export { useMasterAgentChat } from "./useMasterAgentChat"
export type { UseMasterAgentChatReturn } from "./useMasterAgentChat"

export { AgentChatBubble } from "./components/AgentChatBubble"
export { AgentComposer } from "./components/AgentComposer"
export { AgentDockPanel } from "./components/AgentDockPanel"
export { AgentDockShell } from "./components/AgentDockShell"
export { AgentMessageContent } from "./components/AgentMessageContent"
export { AgentSuggestionChips } from "./components/AgentSuggestionChips"
export { AgentTypingIndicator } from "./components/AgentTypingIndicator"
export { MasterAgentPanel } from "./components/MasterAgentPanel"
