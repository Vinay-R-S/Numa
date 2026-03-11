import { TasklistSidebar } from "@/components/tasklist/TasklistSidebar"

export default function TasklistLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dark flex h-screen overflow-hidden bg-background text-foreground">
      <TasklistSidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  )
}
