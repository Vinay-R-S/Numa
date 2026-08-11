/**
 * Slack feature module public surface (NUMA-115 P4, PLAN 5.3 / 21.2).
 */
export * from "./slack.types"
export * from "./slack.api"
export * from "./slack.schema"
export * from "./slack.utils"
export * from "./slack.constants"

export { useSlack } from "./useSlack"
export type { UseSlackReturn } from "./useSlack"
export { useSlackAgent } from "./useSlackAgent"
export type { UseSlackAgentReturn } from "./useSlackAgent"

export { ChannelHeader } from "./components/ChannelHeader"
export { ChannelIcon } from "./components/ChannelIcon"
export { ChannelMessageItem } from "./components/ChannelMessageItem"
export { ChannelSidebar } from "./components/ChannelSidebar"
export { ConnectionBanner } from "./components/ConnectionBanner"
export { MessageComposer } from "./components/MessageComposer"
export { MessageList } from "./components/MessageList"
export { SlackAgentPanel } from "./components/SlackAgentPanel"
export { SlackPageHeader } from "./components/SlackPageHeader"
