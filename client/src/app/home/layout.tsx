import React from "react"
import { AppShell } from "@/components/tasklist/AppShell"

export default function HomeLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>
}
