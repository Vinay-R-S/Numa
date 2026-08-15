"use client"

import { GitBranch, Trophy } from "lucide-react"

import {
  GitHubSection,
  LeetCodeSection,
  ProductivityPageHeader,
  ProductivityPanel,
} from "@/features/productivity"

export default function ProductivityPage() {
  return (
    <div className="flex h-full w-full flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
      <ProductivityPageHeader />

      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-2 min-h-0">
        <ProductivityPanel icon={GitBranch} title="GitHub">
          <GitHubSection />
        </ProductivityPanel>

        <ProductivityPanel icon={Trophy} title="LeetCode">
          <LeetCodeSection />
        </ProductivityPanel>
      </div>
    </div>
  )
}
