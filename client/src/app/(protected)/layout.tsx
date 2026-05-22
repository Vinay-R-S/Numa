"use client"

import React, { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { AppShell } from "@/components/tasklist/AppShell"
import { supabase } from "@/lib/supabase"
import { hasIntegrationBootstrapPending, runIntegrationBootstrap } from "@/lib/bootstrapIntegrations"

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [checkingAuth, setCheckingAuth] = useState(true)

  useEffect(() => {
    let cancelled = false

    const maybeRunBootstrap = async (token: string) => {
      if (!hasIntegrationBootstrapPending()) return
      const result = await runIntegrationBootstrap(token)
      if (result === "done" && !cancelled) {
        router.replace("/home")
      }
    }

    const ensureSession = async () => {
      const token = localStorage.getItem("numa_token")
      if (token) {
        if (!cancelled) setCheckingAuth(false)
        void maybeRunBootstrap(token)
        return
      }

      const { data } = await supabase.auth.getSession()
      const supabaseToken = data.session?.access_token
      if (!supabaseToken) {
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
        if (!res.ok || !json.access_token) {
          router.replace("/auth")
          return
        }

        localStorage.setItem("numa_token", json.access_token)
        if (!cancelled) setCheckingAuth(false)
        void maybeRunBootstrap(json.access_token)
      } catch {
        router.replace("/auth")
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
