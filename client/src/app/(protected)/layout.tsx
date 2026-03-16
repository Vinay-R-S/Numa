"use client"

import React, { useEffect } from "react"
import { useRouter } from "next/navigation"
import { AppShell } from "@/components/tasklist/AppShell"

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem("numa_token")
    if (!token) {
      router.replace("/auth")
    }
  }, [router])

  return <AppShell>{children}</AppShell>
}
