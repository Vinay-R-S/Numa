"use client"

import React, { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { AppShell } from "@/components/tasklist/AppShell"
import { supabase } from "@/lib/supabase"
import { hasIntegrationBootstrapPending, runIntegrationBootstrap } from "@/lib/bootstrapIntegrations"
import { clearToken, getToken, isTokenExpired, storeToken } from "@/lib/session"

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [checkingAuth, setCheckingAuth] = useState(true)

  useEffect(() => {
    let cancelled = false

    // Never `void`-discarded: a throw from the fetch inside became an
    // unhandled rejection and the pending flag stayed set forever, so every
    // later page load retried the same failing bootstrap (NUMA-142 P6, PLAN 7).
    const maybeRunBootstrap = async (token: string) => {
      if (!hasIntegrationBootstrapPending()) return
      try {
        const result = await runIntegrationBootstrap(token)
        // "retry" is not success: navigating on it bounced a user who deep
        // linked to /calendar or /settings to /home because the backend was
        // briefly down (NUMA-142 P6 review).
        if (result === "done" && !cancelled) {
          router.replace("/home")
        }
      } catch {
        // The flag stays set on purpose: the next load retries. Only a
        // completed run clears it.
      }
    }

    const ensureSession = async () => {
      const token = getToken()
      if (token && !isTokenExpired(token)) {
        if (!cancelled) setCheckingAuth(false)
        void maybeRunBootstrap(token).catch(() => undefined)
        return
      }

      // Presence used to be the whole check, so an expired token rendered every
      // protected page against a backend that answered 401 (NUMA-126). Drop it
      // and fall through: the Supabase session usually outlives our 7-day JWT,
      // in which case the exchange below issues a fresh one and the user never
      // sees the sign-in screen.
      if (token) clearToken()

      const { data } = await supabase.auth.getSession()
      if (cancelled) return

      const supabaseToken = data.session?.access_token
      if (!supabaseToken) {
        // `cancelled` guarded the state setters but none of the three
        // navigations, so an unmounted layout still redirected the page the
        // user had already moved to (NUMA-142 P6, PLAN 7).
        router.replace("/auth")
        return
      }

      try {
        const res = await fetch("/api/auth/exchange", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ supabase_token: supabaseToken }),
        })
        const json = await res.json()
        if (cancelled) return

        if (!res.ok || typeof json.access_token !== "string" || !json.access_token) {
          router.replace("/auth")
          return
        }

        storeToken(json.access_token)
        if (!cancelled) setCheckingAuth(false)
        void maybeRunBootstrap(json.access_token).catch(() => undefined)
      } catch {
        if (!cancelled) router.replace("/auth")
      }
    }

    void ensureSession()

    return () => {
      cancelled = true
    }
  }, [router])

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="h-8 w-8 rounded-full border-2 border-muted border-t-foreground animate-spin" />
      </div>
    )
  }

  return <AppShell>{children}</AppShell>
}
