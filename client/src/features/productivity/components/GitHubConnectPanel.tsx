import { GitBranch, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"

export function GitHubConnectPanel({
  token,
  connecting,
  onTokenChange,
  onConnectOAuth,
  onConnectToken,
}: {
  token: string
  connecting: boolean
  onTokenChange: (value: string) => void
  onConnectOAuth: () => void
  onConnectToken: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-10">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/50 ring-1 ring-border/40">
        <GitBranch className="h-7 w-7 text-muted-foreground" />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-foreground">GitHub not connected</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Connect your GitHub account to track contributions
        </p>
      </div>
      <Button size="sm" onClick={onConnectOAuth} className="gap-2">
        <GitBranch className="h-4 w-4" />
        Connect with OAuth
      </Button>
      <div className="w-full max-w-md space-y-2 rounded-xl border border-border/40 bg-background/40 p-3">
        <label htmlFor="github-token" className="text-xs font-semibold text-foreground">
          Or connect with a GitHub token
        </label>
        <div className="flex gap-2">
          <input
            id="github-token"
            type="password"
            value={token}
            onChange={(e) => onTokenChange(e.target.value)}
            placeholder="github_pat_... or ghp_..."
            className="min-w-0 flex-1 rounded-lg border border-border/60 bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
          <Button type="button" size="sm" onClick={onConnectToken} disabled={connecting}>
            {connecting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Connect"}
          </Button>
        </div>
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          Use a fine-grained token with repository read access, or a classic token with repo and read:user.
          This is the most reliable local-dev option for private repos and commit history.
        </p>
      </div>
    </div>
  )
}
