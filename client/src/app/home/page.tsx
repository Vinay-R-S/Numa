"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface User {
  id: string;
  email: string;
  full_name?: string;
}

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("numa_token");
    if (!token) {
      router.replace("/auth");
      return;
    }

    fetch(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.status === 401) {
          localStorage.removeItem("numa_token");
          router.replace("/auth");
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (data) setUser(data);
      })
      .finally(() => setLoading(false));
  }, [router]);

  const handleSignOut = async () => {
    localStorage.removeItem("numa_token");
    router.replace("/auth");
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 rounded-full border-2 border-white/20 border-t-white animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 px-6">
      <h1 className="text-4xl font-extrabold tracking-tight">NUMA</h1>
      {user && (
        <p className="text-muted-foreground text-sm">
          Welcome back,{" "}
          <span className="text-foreground font-medium">
            {user.full_name || user.email}
          </span>
        </p>
      )}
      <button
        onClick={handleSignOut}
        className="mt-4 text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
      >
        Sign out
      </button>
    </div>
  );
}
