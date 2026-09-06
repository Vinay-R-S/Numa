/**
 * One guard for every backend-supplied URL the app navigates to (NUMA-142 P6).
 *
 * Four OAuth flows take an absolute URL out of a JSON response and assign it
 * straight to `location`: the GitHub authorize URL, the Google Calendar
 * authorize URL, the calendar token-health `reconnect_url`, and the Slack
 * authorize URL. Only the first was ever checked, in `productivity.api.ts`,
 * with a comment about a compromised or misconfigured backend - the same
 * hazard, unchecked, at the other three (PLAN 8).
 *
 * The check is a prefix match against the provider's own authorization
 * endpoint, so a redirect can only ever leave for the provider the flow is for.
 */

export const GITHUB_AUTHORIZE_URL_PREFIX = "https://github.com/login/oauth/authorize"
export const GOOGLE_AUTHORIZE_URL_PREFIX = "https://accounts.google.com/o/oauth2/"
export const SLACK_AUTHORIZE_URL_PREFIX = "https://slack.com/oauth/"

/** Prefixes any bootstrap-driven OAuth redirect is allowed to use. */
export const OAUTH_AUTHORIZE_URL_PREFIXES = [
  GITHUB_AUTHORIZE_URL_PREFIX,
  GOOGLE_AUTHORIZE_URL_PREFIX,
  SLACK_AUTHORIZE_URL_PREFIX,
] as const

export function isAllowedExternalUrl(
  url: unknown,
  allowedPrefixes: readonly string[]
): url is string {
  if (typeof url !== "string" || url.length === 0) return false
  return allowedPrefixes.some((prefix) => url.startsWith(prefix))
}

/**
 * Return `url` when it starts with one of `allowedPrefixes`, else throw.
 * `label` names the flow in the error the user sees.
 */
export function assertExternalUrl(
  url: unknown,
  allowedPrefixes: readonly string[],
  label: string
): string {
  if (!isAllowedExternalUrl(url, allowedPrefixes)) {
    throw new Error(`Invalid ${label} authorization URL`)
  }
  return url
}
